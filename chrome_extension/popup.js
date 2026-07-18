let activeTabId = null;
let roiCoords = { t1: null, t2: null, icons: null };
let isCapturing = false;
let logCounter = 1;
let localLogs = [];

const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");
const btnCalibrateT1 = document.getElementById("btnCalibrateT1");
const btnCalibrateT2 = document.getElementById("btnCalibrateT2");
const btnCalibrateIcons = document.getElementById("btnCalibrateIcons");
const btnExport = document.getElementById("btnExport");
const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");

const canvasT1 = document.getElementById("canvasT1");
const canvasIcons = document.getElementById("canvasIcons");
const canvasT2 = document.getElementById("canvasT2");

const lblDuration = document.getElementById("lblDuration");
const lblSamplingMode = document.getElementById("lblSamplingMode");
const lblFramesSampled = document.getElementById("lblFramesSampled");
const lblFramesSent = document.getElementById("lblFramesSent");
const lblFramesRejected = document.getElementById("lblFramesRejected");

const lblPixelDiff = document.getElementById("lblPixelDiff");
const lblSaturationScore = document.getElementById("lblSaturationScore");
const lblBrightness = document.getElementById("lblBrightness");

const lblFeedPresent = document.getElementById("lblFeedPresent");
const lblRapidActive = document.getElementById("lblRapidActive");
const lblNextSend = document.getElementById("lblNextSend");
const lblCooldown = document.getElementById("lblCooldown");
const lblReason = document.getElementById("lblReason");

const logTableBody = document.getElementById("logTableBody");
const btnIgnore = document.getElementById("btnIgnore");

// DOM Initializer
document.addEventListener("DOMContentLoaded", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  activeTabId = tab.id;

  // Sync state from background on popup load
  chrome.runtime.sendMessage({ action: "get-status" }, (response) => {
    if (response) {
      isCapturing = response.isCapturing;
      roiCoords = response.roi;
      logCounter = response.logCounter;
      localLogs = response.logs;
      
      // Update Ignore button styling based on saved state
      updateIgnoreButtonUI(response.isIgnoring);

      // Restore logs
      logTableBody.innerHTML = "";
      localLogs.forEach(log => appendLogTableRowUI(log));
      if (localLogs.length > 0) btnExport.disabled = false;

      if (isCapturing) {
        setUIRunning();
        // Fetch active diagnostics directly from content script
        queryActiveDiagnostics();
      } else {
        setUIStopped();
        if (roiCoords && roiCoords.t1 && roiCoords.t2 && roiCoords.icons) {
          btnStart.disabled = false;
          lblReason.innerText = "CALIBRATION LOADED";
        } else {
          btnStart.disabled = true;
          let count = 0;
          if (roiCoords) {
            if (roiCoords.t1) count++;
            if (roiCoords.t2) count++;
            if (roiCoords.icons) count++;
          }
          lblReason.innerText = `AWAITING CALIBRATION (${count}/3 LOCKED)`;
        }
      }
    }
  });

  btnIgnore.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "toggle-ignore" }, (response) => {
      if (response) {
        updateIgnoreButtonUI(response.isIgnoring);
      }
    });
  });

  checkVideoStatus();
});

function updateIgnoreButtonUI(isIgnoring) {
  if (isIgnoring) {
    btnIgnore.innerText = "IGNORING";
    btnIgnore.style.backgroundColor = "#c0392b";
    btnIgnore.style.borderColor = "#c0392b";
    btnIgnore.style.color = "#fff";
  } else {
    btnIgnore.innerText = "Ignore";
    btnIgnore.style.backgroundColor = "#1a202c";
    btnIgnore.style.borderColor = "#2d3748";
    btnIgnore.style.color = "#e2e8f0";
  }
}

function checkVideoStatus() {
  try {
    chrome.tabs.sendMessage(activeTabId, { action: "detect-video" }, (response) => {
      if (chrome.runtime.lastError || !response || !response.hasVideo) {
        if (!isCapturing) {
          statusDot.className = "status-dot error";
          statusLabel.innerText = "NO STREAM FOUND";
          btnCalibrate.disabled = true;
        }
      } else {
        if (!isCapturing) {
          statusDot.className = "status-dot";
          statusLabel.innerText = "ONLINE (IDLE)";
          btnCalibrate.disabled = false;
        }
      }
    });
  } catch (err) {
    if (!isCapturing) {
      statusDot.className = "status-dot error";
      statusLabel.innerText = "RELOAD ACTIVE TAB";
    }
  }
}

function queryActiveDiagnostics() {
  if (!isCapturing) return;
  chrome.tabs.sendMessage(activeTabId, { action: "get-diagnostics" }, (response) => {
    if (response) {
      updateDiagnosticsUI(response);
    }
  });
}

// Calibrate Trigger T1
btnCalibrateT1.addEventListener("click", () => {
  if (!activeTabId) return;
  chrome.tabs.sendMessage(activeTabId, { action: "start-calibration", target: "t1" }, () => {
    lblReason.innerText = "DRAWING ROI OVER T1 NAME...";
  });
});

// Calibrate Trigger T2
btnCalibrateT2.addEventListener("click", () => {
  if (!activeTabId) return;
  chrome.tabs.sendMessage(activeTabId, { action: "start-calibration", target: "t2" }, () => {
    lblReason.innerText = "DRAWING ROI OVER T2 NAME...";
  });
});

// Calibrate Trigger Icons
btnCalibrateIcons.addEventListener("click", () => {
  if (!activeTabId) return;
  chrome.tabs.sendMessage(activeTabId, { action: "start-calibration", target: "icons" }, () => {
    lblReason.innerText = "DRAWING ROI OVER ICONS...";
  });
});

// Start Ingest
btnStart.addEventListener("click", () => {
  if (!activeTabId || !roiCoords) return;
  
  // Start the background process state
  chrome.runtime.sendMessage({
    action: "start-capture",
    tabId: activeTabId,
    roi: roiCoords
  }, () => {
    // Start sampling engine inside content script
    chrome.tabs.sendMessage(activeTabId, {
      action: "start-sampling",
      roi: roiCoords
    }, () => {
      setUIRunning();
    });
  });
});

// Stop Ingest
btnStop.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "stop-capture" }, () => {
    chrome.tabs.sendMessage(activeTabId, { action: "stop-sampling" }, () => {
      setUIStopped();
    });
  });
});

function setUIRunning() {
  isCapturing = true;
  btnStart.style.display = "none";
  btnStop.style.display = "block";
  btnCalibrateT1.disabled = true;
  btnCalibrateT2.disabled = true;
  btnCalibrateIcons.disabled = true;
  btnExport.disabled = false;
  
  statusDot.className = "status-dot active";
  statusLabel.innerText = "INGESTING (NORMAL)";
}

function setUIStopped() {
  isCapturing = false;
  btnStop.style.display = "none";
  btnStart.style.display = "block";
  btnCalibrateT1.disabled = false;
  btnCalibrateT2.disabled = false;
  btnCalibrateIcons.disabled = false;
  
  statusDot.className = "status-dot";
  statusLabel.innerText = "ONLINE (IDLE)";
  lblSamplingMode.innerText = "-";
  lblDuration.innerText = "-";
  lblFramesSampled.innerText = "-";
  lblFramesSent.innerText = "-";
  lblFramesRejected.innerText = "-";
}

// Receive messages from content script & background worker
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === "update-roi" || message.action === "calibration-locked" || message.action === "calibration-draft") {
    roiCoords = message.roi;
    let count = 0;
    if (roiCoords) {
      if (roiCoords.t1) count++;
      if (roiCoords.t2) count++;
      if (roiCoords.icons) count++;
    }
    if (count === 3) {
      btnStart.disabled = false;
      lblReason.innerText = "ROI LOCKED & READY";
    } else {
      btnStart.disabled = true;
      lblReason.innerText = `AWAITING CALIBRATION (${count}/3 LOCKED)`;
    }
  }
  else if (message.action === "mode-change") {
    if (isCapturing) {
      if (message.mode === "RAPID") {
        statusDot.className = "status-dot rapid";
        statusLabel.innerText = "INGESTING (RAPID)";
      } else {
        statusDot.className = "status-dot active";
        statusLabel.innerText = "INGESTING (NORMAL)";
      }
    }
  }
  else if (message.action === "frame-previews") {
    renderPreviews(message.t1, message.icons, message.t2);
    
    // Process real-time engine diagnostics (V0.14)
    if (message.diagnostics) {
      updateDiagnosticsUI(message.diagnostics);
    }
  } 
  else if (message.action === "new-log-entry") {
    appendLogTableRowUI(message.log);
    btnExport.disabled = false;
  }
  else if (message.action === "tab-disconnected") {
    setUIStopped();
    lblReason.innerText = "TAB DISCONNECTED";
    checkVideoStatus();
  }
});

function formatDuration(sec) {
  if (!sec && sec !== 0) return "-";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

function updateDiagnosticsUI(diag) {
  // Mode & Temporal
  lblSamplingMode.innerText = diag.engine.mode || "-";
  lblSamplingMode.className = diag.engine.mode === "RAPID" ? "diag-val alert" : "diag-val highlight";
  lblDuration.innerText = formatDuration(diag.engine.sessionDurationSec);
  
  // Pipeline counters
  lblFramesSampled.innerText = diag.engine.framesSampled || "0";
  lblFramesSent.innerText = diag.scheduler.framesSent || "0";
  lblFramesRejected.innerText = diag.scheduler.framesRejected || "0";
  
  // Pixel analysis
  lblPixelDiff.innerText = diag.pixelDiff !== undefined ? `${diag.pixelDiff} px` : "-";
  
  const detector = diag.feedDetector || {};
  lblSaturationScore.innerText = detector.saturationScore !== undefined ? `${detector.saturationScore}` : "-";
  lblSaturationScore.className = detector.feedPresent ? "diag-val alert" : "diag-val";
  lblBrightness.innerText = detector.avgBrightness !== undefined ? `${detector.avgBrightness}` : "-";
  
  // Decision Engine
  lblFeedPresent.innerText = detector.feedPresent ? "YES" : "NO";
  lblFeedPresent.className = detector.feedPresent ? "diag-val alert" : "diag-val";
  
  lblRapidActive.innerText = diag.engine.mode === "RAPID" ? "YES" : "NO";
  lblRapidActive.className = diag.engine.mode === "RAPID" ? "diag-val alert" : "diag-val";
  
  if (!detector.feedPresent) {
    lblNextSend.innerText = "SUSPENDED";
    lblNextSend.className = "diag-val neutral";
  } else {
    lblNextSend.innerText = diag.scheduler.nextSendIn !== undefined ? `${diag.scheduler.nextSendIn}ms` : "-";
    lblNextSend.className = "diag-val alert";
  }
  lblCooldown.innerText = diag.engine.cooldownActive ? "ACTIVE" : "INACTIVE";
  lblCooldown.className = diag.engine.cooldownActive ? "diag-val alert" : "diag-val neutral";
  
  // Decide reason text
  if (diag.engine.mode === "NORMAL") {
    lblReason.innerText = "MONITORING IDLE FEED";
  } else if (diag.engine.mode === "RAPID") {
    if (detector.feedPresent) {
      const region = detector.detectedRegion ? detector.detectedRegion.toUpperCase() : "UNKNOWN";
      lblReason.innerText = `ACTIVE FEED IN ${region}`;
    } else {
      lblReason.innerText = "COOLDOWN PENDING EXIT";
    }
  }
}

// Render previews for all 3 segments separately in real-time
function renderPreviews(t1Url, iconsUrl, t2Url) {
  const drawToCanvas = (canvas, dataUrl) => {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!dataUrl) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };
    img.src = dataUrl;
  };

  drawToCanvas(canvasT1, t1Url);
  drawToCanvas(canvasIcons, iconsUrl);
  drawToCanvas(canvasT2, t2Url);
}

function appendLogTableRowUI(log) {
  const row = document.createElement("tr");
  row.className = "new-log";
  
  row.innerHTML = `
    <td style="text-align: center; font-weight: bold; color: #bfa15f;">${log.log_num}</td>
    <td style="text-align: center; color: #d35400;">${log.layout}</td>
    <td>${log.t1}</td>
    <td style="text-align: center;">${log.i1}</td>
    <td style="text-align: center; font-weight: bold; color: #27ae60;">${log.i2}</td>
    <td>${log.t2}</td>
  `;
  
  logTableBody.appendChild(row);
  const container = document.querySelector(".table-container");
  if (container) container.scrollTop = container.scrollHeight;
}

// Safe CSV Export using W3C Blob + chrome.downloads API
btnExport.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "get-status" }, (response) => {
    if (!response || response.logs.length === 0) return;
    
    let csvContent = "Log #,Layout Type,T1,I1,I2,T2\n";
    response.logs.forEach(log => {
      csvContent += `"${log.log_num}","${log.layout}","${log.t1}","${log.i1}","${log.i2}","${log.t2}"\n`;
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const blobUrl = URL.createObjectURL(blob);

    const now = new Date();
    const ts = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`;

    chrome.downloads.download({
      url: blobUrl,
      filename: `FragEngine_QL_${ts}.csv`,
      saveAs: false
    }, () => {
      URL.revokeObjectURL(blobUrl);
    });
  });
});
