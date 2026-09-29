const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, spawnSync } = require('child_process');
const readline = require('readline');

let mainWindow = null;
let activeProcess = null;
let activeOutputFile = null;
let isCancelled = false;

function getBackendExecutable() {
  const isWin = process.platform === 'win32';
  const venvDir = path.join(__dirname, '..', '.venv', isWin ? 'Scripts' : 'bin');
  
  // 1. Check compiled entrypoint script in .venv
  const exePath = path.join(venvDir, isWin ? 'video-formatter.exe' : 'video-formatter');
  if (fs.existsSync(exePath)) {
    return { cmd: exePath, argsPrefix: [] };
  }
  
  // 2. Check python executable in .venv
  const pyPath = path.join(venvDir, isWin ? 'python.exe' : 'python');
  if (fs.existsSync(pyPath)) {
    return { cmd: pyPath, argsPrefix: ['-m', 'src.my_app.main'] };
  }
  
  // 3. Fallback to system PATH
  return { cmd: 'video-formatter', argsPrefix: [] };
}

function killProcessTree(pid) {
  if (!pid) return;
  if (process.platform === 'win32') {
    try {
      // Force kill the entire process tree (/T = tree kill, /F = force)
      // This kills python AND all child ffmpeg-win-x86_64-v7.1.exe processes immediately!
      spawnSync('taskkill', ['/pid', pid.toString(), '/T', '/F']);
    } catch (err) {
      console.error('Error executing taskkill:', err);
    }
  } else {
    try {
      process.kill(-pid, 'SIGKILL');
    } catch (e) {
      try { process.kill(pid, 'SIGKILL'); } catch (_) {}
    }
  }
}

function createWindow() {
  Menu.setApplicationMenu(null); // Clean window without old-school menubar

  mainWindow = new BrowserWindow({
    width: 1080,
    height: 800,
    minWidth: 920,
    minHeight: 660,
    backgroundColor: '#070a13',
    title: 'PureClip - Video Formatter & Compressor',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'app', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

// ---------------- IPC Handlers ----------------

// Select input video / audio file
ipcMain.handle('dialog:select-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Video or Audio File',
    properties: ['openFile'],
    filters: [
      {
        name: 'Media Files',
        extensions: ['mp4', 'mov', 'mkv', 'webm', 'avi', 'flv', 'wmv', 'm4v', 'ts', 'mp3', 'wav', 'aac', 'flac', 'ogg', 'gif'],
      },
      { name: 'All Files', extensions: ['*'] },
    ],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Select custom output directory
ipcMain.handle('dialog:select-output-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Output Directory',
    properties: ['openDirectory', 'createDirectory'],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Probe file metadata using Python backend
ipcMain.handle('video:probe', async (_event, filePath) => {
  return new Promise((resolve, reject) => {
    const { cmd, argsPrefix } = getBackendExecutable();
    const args = [...argsPrefix, filePath, '--info', '--json'];

    const child = spawn(cmd, args, {
      cwd: path.join(__dirname, '..'),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });

    let probeResult = null;
    let errorOutput = '';

    const rl = readline.createInterface({ input: child.stdout });
    rl.on('line', (line) => {
      try {
        const parsed = JSON.parse(line.trim());
        if (parsed.type === 'probe') {
          probeResult = parsed.data;
        } else if (parsed.type === 'error') {
          errorOutput = parsed.data.message || 'Probe error';
        }
      } catch (e) {
        // ignore non-json banner lines
      }
    });

    child.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    child.on('close', (code) => {
      if (code === 0 && probeResult) {
        resolve(probeResult);
      } else {
        reject(new Error(errorOutput || ('Probe exited with code ' + code)));
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
});

// Start conversion pipeline with live stdout progress streaming
ipcMain.handle('video:convert', async (_event, options) => {
  if (activeProcess) {
    throw new Error('A conversion task is already in progress.');
  }
  isCancelled = false;

  const { cmd, argsPrefix } = getBackendExecutable();
  const args = [...argsPrefix, options.inputPath, '--json'];

  if (options.format) args.push('-f', options.format);
  if (options.preset) args.push('-p', options.preset);
  if (options.outputPath) args.push('-o', options.outputPath);
  if (options.scale) args.push('--scale', options.scale);
  if (options.fps) args.push('--fps', String(options.fps));
  if (options.crf !== undefined && options.crf !== null && options.crf !== '') args.push('--crf', String(options.crf));
  if (options.targetMb) args.push('--target-mb', String(options.targetMb));
  if (options.audioBitrate) args.push('--audio-bitrate', options.audioBitrate);
  if (options.keepMetadata) args.push('--keep-metadata');
  if (options.noFaststart) args.push('--no-faststart');

  // Track expected output path for cleanup on cancellation
  if (options.outputPath) {
    activeOutputFile = options.outputPath;
  } else {
    const inputDir = path.dirname(options.inputPath);
    const parentDir = path.basename(inputDir) === 'output' ? inputDir : path.join(inputDir, 'output');
    const baseName = path.basename(options.inputPath, path.extname(options.inputPath));
    activeOutputFile = path.join(parentDir, baseName + '_formatted.' + (options.format || 'mp4'));
  }

  return new Promise((resolve, reject) => {
    activeProcess = spawn(cmd, args, {
      cwd: path.join(__dirname, '..'),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });

    const child = activeProcess;
    let finalResult = null;
    let errorMsg = '';

    const rl = readline.createInterface({ input: child.stdout });
    rl.on('line', (line) => {
      try {
        const event = JSON.parse(line.trim());
        if (event.type === 'progress') {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('video:progress', event.data);
          }
        } else if (event.type === 'complete') {
          finalResult = event.data;
          activeOutputFile = null; // Successfully completed, do not delete!
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('video:complete', event.data);
          }
        } else if (event.type === 'error') {
          errorMsg = event.data.message || 'Conversion failed';
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('video:error', errorMsg);
          }
        }
      } catch (e) {
        // non-json lines
      }
    });

    child.stderr.on('data', (chunk) => {
      errorMsg += chunk.toString();
    });

    child.on('close', (code) => {
      activeProcess = null;
      if (isCancelled) {
        reject(new Error('Conversion was cancelled by user.'));
        return;
      }
      if (code === 0 && finalResult) {
        resolve(finalResult);
      } else if (code === 130) {
        reject(new Error('Conversion was cancelled by user.'));
      } else {
        reject(new Error(errorMsg || ('Conversion failed with code ' + code)));
      }
    });

    child.on('error', (err) => {
      activeProcess = null;
      reject(err);
    });
  });
});

// Cancel active conversion & kill entire process tree
ipcMain.handle('video:cancel', async () => {
  isCancelled = true;
  if (activeProcess && activeProcess.pid) {
    const pid = activeProcess.pid;
    activeProcess = null;

    // Immediately kill process tree (Python + FFmpeg)
    killProcessTree(pid);

    // Clean up partial locked file after process releases file handle
    if (activeOutputFile) {
      const fileToRemove = activeOutputFile;
      activeOutputFile = null;
      setTimeout(() => {
        try {
          if (fs.existsSync(fileToRemove)) {
            fs.unlinkSync(fileToRemove);
          }
        } catch (_) {}
      }, 500);
    }

    return true;
  }
  return false;
});

// Open external link in system web browser
ipcMain.handle('app:open-external', async (_event, url) => {
  if (url && (url.startsWith('https://') || url.startsWith('http://'))) {
    shell.openExternal(url);
    return true;
  }
  return false;
});

// Open file / folder in OS File Explorer
ipcMain.handle('video:open-explorer', async (_event, targetPath) => {
  if (targetPath && fs.existsSync(targetPath)) {
    shell.showItemInFolder(targetPath);
    return true;
  }
  return false;
});

// ---------------- App Lifecycle ----------------
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  if (activeProcess && activeProcess.pid) {
    killProcessTree(activeProcess.pid);
    activeProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
