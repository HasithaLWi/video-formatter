const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  selectFile: () => ipcRenderer.invoke('dialog:select-file'),
  selectOutputDir: () => ipcRenderer.invoke('dialog:select-output-dir'),
  probeFile: (filePath) => ipcRenderer.invoke('video:probe', filePath),
  startConversion: (options) => ipcRenderer.invoke('video:convert', options),
  cancelConversion: () => ipcRenderer.invoke('video:cancel'),
  openInExplorer: (filePath) => ipcRenderer.invoke('video:open-explorer', filePath),
  
  onProgress: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('video:progress', handler);
    return () => ipcRenderer.removeListener('video:progress', handler);
  },
  
  onComplete: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('video:complete', handler);
    return () => ipcRenderer.removeListener('video:complete', handler);
  },
  
  onError: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('video:error', handler);
    return () => ipcRenderer.removeListener('video:error', handler);
  },
  
  openExternalUrl: (url) => ipcRenderer.invoke('app:open-external', url),
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('video:progress');
    ipcRenderer.removeAllListeners('video:complete');
    ipcRenderer.removeAllListeners('video:error');
  }
});