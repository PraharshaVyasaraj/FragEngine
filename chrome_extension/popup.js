let activeTabId = null;
let roiCoords = null;
let isCapturing = false;
let logCounter = 1;
let localLogs = [];

const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");
const btnCalibrate = document.getElementById("btnCalibrate");
const btnDashboard = document.getElementById("btnDashboard");
const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");

const canvasRaw = document.getElementById("canvasRaw");
const canvasBin = document.getElementById("canvasBin");

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
const chkAlwaysOn = document.getElementById("chkAlwaysOn");

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
        if (roiCoords) {
          btnStart.disabled = false;
          lblReason.innerText = "CALIBRATION LOADED";
        } else {
          lblReason.innerText = "AWAITING CALIBRATION";
        }
      }
    }
  });

  // Restore checkbox preference
  chrome.storage.local.get(["alwaysOn"], (result) => {
    if (result.alwaysOn) {
      chkAlwaysOn.checked = true;
    }
  });

  chkAlwaysOn.addEventListener("change", () => {
    chrome.storage.local.set({ alwaysOn: chkAlwaysOn.checked });
  });

  checkVideoStatus();
});

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

// Calibrate Trigger
btnCalibrate.addEventListener("click", () => {
  if (!activeTabId) return;
  chrome.tabs.sendMessage(activeTabId, { action: "start-calibration" }, () => {
    lblReason.innerText = "DRAWING ROI OVER KILL FEED...";
  });
});

// Launch Live Telemetry HUD Dashboard
if (btnDashboard) {
  btnDashboard.addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("dashboard.html") });
  });
}

// Export Analytics Report
const btnExportAnalytics = document.getElementById("btnExportAnalytics");
if (btnExportAnalytics) {
  btnExportAnalytics.addEventListener("click", () => {
    fetch("http://127.0.0.1:5000/api/analytics/export")
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success" && data.report) {
          const blob = new Blob([JSON.stringify(data.report, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `fragengine_match_report_${Date.now()}.json`;
          a.click();
          URL.revokeObjectURL(url);
        } else {
          alert("Failed to generate analytics report. Ensure server is active.");
        }
      })
      .catch((err) => alert("Could not connect to Flask server analytics endpoint."));
  });
}

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
  btnCalibrate.disabled = true;
  btnExport.disabled = false;
  
  statusDot.className = "status-dot active";
  statusLabel.innerText = "INGESTING (NORMAL)";
}

function setUIStopped() {
  isCapturing = false;
  btnStop.style.display = "none";
  btnStart.style.display = "block";
  btnCalibrate.disabled = false;
  
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
  if (message.action === "update-roi") {
    roiCoords = message.roi;
    btnStart.disabled = false;
    lblReason.innerText = "ROI LOCKED & READY";
  } 
  else if (message.action === "calibration-draft") {
    roiCoords = message.roi;
    btnStart.disabled = false;
    lblReason.innerText = "ROI LOCKED & READY";
  }
  else if (message.action === "mode-change") {
    if (isCapturing) {
      if (message.mode === "RAPID") {
        statusDot.className = "status-dot rapid";
        statusLabel.innerText = "INGESTING (RAPID)";
      } else if (message.mode === "REST") {
        statusDot.className = "status-dot rest";
        statusLabel.innerText = "INGESTING (REST)";
      } else {
        statusDot.className = "status-dot active";
        statusLabel.innerText = "INGESTING (NORMAL)";
      }
    }
  }
  else if (message.action === "frame-previews") {
    renderRawPreview(message.raw);
    
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
  if (!diag || !diag.engine) return;

  // Mode & Duration
  lblSamplingMode.innerText = diag.engine.mode || "STANDARD_250MS";
  lblSamplingMode.className = "diag-val highlight";
  
  const sec = diag.engine.sessionDurationMs ? Math.floor(diag.engine.sessionDurationMs / 1000) : 0;
  lblDuration.innerText = formatDuration(sec);
  
  // Pipeline counters
  lblFramesSampled.innerText = diag.engine.framesSampled || "0";
  if (diag.scheduler) {
    lblFramesSent.innerText = diag.scheduler.framesSent || "0";
    lblFramesRejected.innerText = diag.scheduler.framesRejected || "0";
  }
  
  // Pixel analysis
  lblPixelDiff.innerText = diag.pixelDiff !== undefined ? `${diag.pixelDiff} px` : "-";
  
  const detector = diag.feedDetector || {};
  lblSaturationScore.innerText = detector.saturationScore !== undefined ? `${detector.saturationScore}` : "-";
  lblSaturationScore.className = detector.feedPresent ? "diag-val alert" : "diag-val";
  lblBrightness.innerText = detector.avgBrightness !== undefined ? `${detector.avgBrightness}` : "-";
  
  // Decision Engine
  lblNextSend.innerText = "250ms";
  lblNextSend.className = "diag-val highlight";
  lblCooldown.innerText = "STANDBY";
  lblCooldown.className = "diag-val neutral";
  
  lblReason.innerText = detector.feedPresent ? "KILL FEED DETECTED" : "INGESTING AT 250MS FIXED RATE";
}

// Render previews (Canvas Raw and Canvas Bin)
function renderRawPreview(dataUrl) {
  if (!dataUrl) return;
  const img = new Image();
  img.onload = () => {
    canvasRaw.width = img.width;
    canvasRaw.height = img.height;
    const ctxRaw = canvasRaw.getContext("2d");
    ctxRaw.drawImage(img, 0, 0);

    canvasBin.width = img.width;
    canvasBin.height = img.height;
    const ctxBin = canvasBin.getContext("2d", { willReadFrequently: true });
    ctxBin.drawImage(img, 0, 0);
    const imgData = ctxBin.getImageData(0, 0, canvasBin.width, canvasBin.height);
    const data = imgData.data;
    
    // Apply local binarization preview
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i+1];
      const b = data[i+2];
      const v = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const thresh = v > 180 ? 255 : 0;
      data[i] = thresh;
      data[i+1] = thresh;
      data[i+2] = thresh;
    }
    ctxBin.putImageData(imgData, 0, 0);
  };
  img.src = dataUrl;
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
