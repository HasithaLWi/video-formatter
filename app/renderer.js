// ====================================================================
// Video Formatter Renderer Logic & State Management
// ====================================================================

let currentFilePath = null;
let currentProbe = null;
let selectedFormat = 'mp4';
let selectedPreset = 'balanced';
let customOutputDir = null;
let lastResult = null;
let isUserCancelling = false;

// DOM Elements
const dropzoneSection = document.getElementById('dropzoneSection');
const dropzone = document.getElementById('dropzone');
const browseBtn = document.getElementById('browseBtn');

const configSection = document.getElementById('configSection');
const videoPreview = document.getElementById('videoPreview');
const audioPlaceholder = document.getElementById('audioPlaceholder');
const changeFileBtn = document.getElementById('changeFileBtn');

const metaFileName = document.getElementById('metaFileName');
const metaFileSize = document.getElementById('metaFileSize');
const metaRes = document.getElementById('metaRes');
const metaAspect = document.getElementById('metaAspect');
const metaDuration = document.getElementById('metaDuration');
const metaVCodec = document.getElementById('metaVCodec');
const metaFps = document.getElementById('metaFps');
const metaACodec = document.getElementById('metaACodec');

const formatPills = document.querySelectorAll('.format-pills .pill');
const presetCards = document.querySelectorAll('.preset-card');
const presetGroup = document.getElementById('presetGroup');
const stripMetadataCheck = document.getElementById('stripMetadata');
const faststartCheck = document.getElementById('faststart');
const faststartCard = document.getElementById('faststartCard');

const scaleSelect = document.getElementById('scaleSelect');
const customScaleInput = document.getElementById('customScaleInput');
const targetMbInput = document.getElementById('targetMbInput');
const fpsSelect = document.getElementById('fpsSelect');
const outputDirInput = document.getElementById('outputDirInput');
const selectDirBtn = document.getElementById('selectDirBtn');
const convertBtn = document.getElementById('convertBtn');

const progressSection = document.getElementById('progressSection');
const progressBarFill = document.getElementById('progressBarFill');
const statPct = document.getElementById('statPct');
const statSpeed = document.getElementById('statSpeed');
const statFps = document.getElementById('statFps');
const statEta = document.getElementById('statEta');
const cancelBtn = document.getElementById('cancelBtn');

const completeSection = document.getElementById('completeSection');
const compOrigSize = document.getElementById('compOrigSize');
const compNewSize = document.getElementById('compNewSize');
const savingsBadge = document.getElementById('savingsBadge');
const chipFormat = document.getElementById('chipFormat');
const chipElapsed = document.getElementById('chipElapsed');
const chipPrivacy = document.getElementById('chipPrivacy');
const openExplorerBtn = document.getElementById('openExplorerBtn');
const convertAnotherBtn = document.getElementById('convertAnotherBtn');

// ---------------- File Selection & Probing ----------------
async function handleFileSelection(filePath) {
  if (!filePath) return;
  currentFilePath = filePath;

  try {
    const probe = await window.electronAPI.probeFile(filePath);
    currentProbe = probe;
    displayMediaInfo(probe);

    dropzoneSection.classList.add('hidden');
    completeSection.classList.add('hidden');
    configSection.classList.remove('hidden');
  } catch (err) {
    alert('Failed to inspect media file: ' + err.message);
  }
}

function displayMediaInfo(info) {
  metaFileName.textContent = info.file_name;
  metaFileSize.textContent = `${info.file_size_mb.toFixed(2)} MB`;
  metaRes.textContent = info.resolution_str || 'N/A';
  metaAspect.textContent = info.aspect_ratio || 'N/A';
  metaDuration.textContent = info.duration_str || `${info.duration_seconds}s`;
  metaVCodec.textContent = info.video_codec ? info.video_codec.toUpperCase() : 'None (Audio)';
  metaFps.textContent = info.fps ? `${info.fps.toFixed(0)} fps` : 'N/A';
  metaACodec.textContent = info.audio_codec ? info.audio_codec.toUpperCase() : 'None';

  // Video Preview Player
  if (info.has_video) {
    videoPreview.classList.remove('hidden');
    audioPlaceholder.classList.add('hidden');
    videoPreview.src = `file://${info.file_path}`;
  } else {
    videoPreview.classList.add('hidden');
    audioPlaceholder.classList.remove('hidden');
  }
}

// Browse Button
browseBtn.addEventListener('click', async () => {
  const file = await window.electronAPI.selectFile();
  if (file) handleFileSelection(file);
});

changeFileBtn.addEventListener('click', async () => {
  const file = await window.electronAPI.selectFile();
  if (file) handleFileSelection(file);
});

// Drag & Drop
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('drag-over');
});

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('drag-over');
});

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0];
    if (file.path) handleFileSelection(file.path);
  }
});

// ---------------- Format & Preset Controls ----------------
formatPills.forEach((pill) => {
  pill.addEventListener('click', () => {
    formatPills.forEach((p) => p.classList.remove('active'));
    pill.classList.add('active');
    selectedFormat = pill.dataset.format;

    // Audio or GIF specific adjustments
    if (selectedFormat === 'mp3') {
      presetGroup.classList.add('hidden');
      faststartCard.classList.add('hidden');
    } else if (selectedFormat === 'gif') {
      presetGroup.classList.add('hidden');
      faststartCard.classList.add('hidden');
    } else {
      presetGroup.classList.remove('hidden');
      faststartCard.classList.remove('hidden');

      // WebM requires VP9 encoding; if stream_copy was active, auto-switch to balanced
      if (selectedFormat === 'webm' && selectedPreset === 'stream_copy') {
        selectedPreset = 'balanced';
        presetCards.forEach((c) => {
          const r = c.querySelector('input');
          if (r && r.value === 'balanced') {
            r.checked = true;
            c.classList.add('active');
          } else {
            c.classList.remove('active');
          }
        });
      }
    }
  });
});

presetCards.forEach((card) => {
  card.addEventListener('click', () => {
    presetCards.forEach((c) => c.classList.remove('active'));
    card.classList.add('active');
    const radio = card.querySelector('input');
    radio.checked = true;
    selectedPreset = radio.value;
  });
});

scaleSelect.addEventListener('change', () => {
  if (scaleSelect.value === 'custom') {
    customScaleInput.classList.remove('hidden');
    customScaleInput.focus();
  } else {
    customScaleInput.classList.add('hidden');
  }
});

selectDirBtn.addEventListener('click', async () => {
  const dir = await window.electronAPI.selectOutputDir();
  if (dir) {
    customOutputDir = dir;
    outputDirInput.value = dir;
  }
});

// ---------------- Conversion Execution ----------------
convertBtn.addEventListener('click', async () => {
  if (!currentFilePath) return;

  // Resolve Scale
  let scaleVal = scaleSelect.value;
  if (scaleVal === 'custom') {
    scaleVal = customScaleInput.value.trim();
  }

  // Resolve Output Path if custom folder chosen
  let destPath = null;
  if (customOutputDir) {
    const origBase = currentProbe ? currentProbe.file_name.substring(0, currentProbe.file_name.lastIndexOf('.')) : 'output';
    destPath = `${customOutputDir}\\${origBase}_formatted.${selectedFormat}`;
  }

  const options = {
    inputPath: currentFilePath,
    format: selectedFormat,
    preset: selectedPreset,
    outputPath: destPath,
    scale: scaleVal || null,
    fps: fpsSelect.value ? parseInt(fpsSelect.value) : null,
    targetMb: targetMbInput.value ? parseFloat(targetMbInput.value) : null,
    keepMetadata: !stripMetadataCheck.checked,
    noFaststart: !faststartCheck.checked,
  };

  // Reset & Show progress modal
  progressBarFill.style.width = '0%';
  statPct.textContent = '0.0%';
  statSpeed.textContent = '1.0x';
  statFps.textContent = '-- fps';
  statEta.textContent = 'Calculating...';
  progressSection.classList.remove('hidden');

  isUserCancelling = false;
  try {
    const result = await window.electronAPI.startConversion(options);
    handleConversionComplete(result);
  } catch (err) {
    progressSection.classList.add('hidden');
    const msg = (err.message || '').toLowerCase();
    if (!isUserCancelling && !msg.includes('cancel') && !msg.includes('130')) {
      alert('Conversion Error: ' + err.message);
    }
    isUserCancelling = false;
  }
});

cancelBtn.addEventListener('click', async () => {
  isUserCancelling = true;
  progressSection.classList.add('hidden');
  await window.electronAPI.cancelConversion();
});

// ---------------- Realtime Progress Events ----------------
window.electronAPI.onProgress((data) => {
  const pct = Math.min(100, Math.max(0, data.percent));
  progressBarFill.style.width = `${pct}%`;
  statPct.textContent = `${pct.toFixed(1)}%`;
  statSpeed.textContent = data.speed || '1.0x';
  statFps.textContent = data.fps > 0 ? `${data.fps.toFixed(0)} fps` : '-- fps';
  statEta.textContent = data.eta_seconds > 0 ? `${Math.round(data.eta_seconds)}s` : '0s';
});

function handleConversionComplete(result) {
  lastResult = result;
  progressSection.classList.add('hidden');
  configSection.classList.add('hidden');
  completeSection.classList.remove('hidden');

  compOrigSize.textContent = `${result.original_size_mb.toFixed(2)} MB`;
  compNewSize.textContent = `${result.output_size_mb.toFixed(2)} MB`;

  if (result.savings_pct > 0) {
    savingsBadge.innerHTML = `🎉 Space Saved: <strong>${(result.savings_bytes / (1024 * 1024)).toFixed(2)} MB (-${result.savings_pct.toFixed(1)}%)</strong>`;
    savingsBadge.style.color = '#34d399';
  } else if (result.savings_pct < 0) {
    savingsBadge.innerHTML = `File increased by +${Math.abs(result.savings_pct).toFixed(1)}%`;
    savingsBadge.style.color = '#fbbf24';
  } else {
    savingsBadge.innerHTML = `No size change`;
  }

  chipFormat.textContent = `Format: ${result.target_format.toUpperCase()}`;
  chipElapsed.textContent = `Time: ${result.elapsed_time_seconds.toFixed(2)}s`;
  chipPrivacy.textContent = result.metadata_stripped ? '🛡️ Privacy: Cleaned' : 'Metadata Preserved';
}

openExplorerBtn.addEventListener('click', async () => {
  if (lastResult && lastResult.output_path) {
    await window.electronAPI.openInExplorer(lastResult.output_path);
  }
});

convertAnotherBtn.addEventListener('click', () => {
  completeSection.classList.add('hidden');
  dropzoneSection.classList.remove('hidden');
  currentFilePath = null;
  currentProbe = null;
  videoPreview.src = '';
});


// ---------------- About & License Modal & External Links ----------------
const aboutBtn = document.getElementById('aboutBtn');
const aboutModal = document.getElementById('aboutModal');
const closeAboutBtn = document.getElementById('closeAboutBtn');
const closeAboutModalBtn = document.getElementById('closeAboutModalBtn');
const footerGithubLink = document.getElementById('footerGithubLink');
const aboutGithubLink = document.getElementById('aboutGithubLink');

function openAboutModal() {
  if (aboutModal) aboutModal.classList.remove('hidden');
}

function closeAboutModal() {
  if (aboutModal) aboutModal.classList.add('hidden');
}

if (aboutBtn) aboutBtn.addEventListener('click', openAboutModal);
if (closeAboutBtn) closeAboutBtn.addEventListener('click', closeAboutModal);
if (closeAboutModalBtn) closeAboutModalBtn.addEventListener('click', closeAboutModal);

// Open external browser on GitHub link click
function handleExternalLink(e, url) {
  e.preventDefault();
  if (window.electronAPI && window.electronAPI.openExternalUrl) {
    window.electronAPI.openExternalUrl(url);
  }
}

if (footerGithubLink) {
  footerGithubLink.addEventListener('click', (e) => handleExternalLink(e, 'https://github.com/HasithaLWi'));
}
if (aboutGithubLink) {
  aboutGithubLink.addEventListener('click', (e) => handleExternalLink(e, 'https://github.com/HasithaLWi'));
}
