let activeTabId = null;
let roiCoords = null;
let draftRoiCoords = null;
let isCapturing = false;
let logCounter = 1;
let localLogs = []; 

const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");
const btnCalibrate = document.getElementById("btnCalibrate");
const btnLock = document.getElementById("btnLock");
const btnExport = document.getElementById("btnExport");
const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");

const canvasRaw = document.getElementById("canvasRaw");
const canvasBin = document.getElementById("canvasBin");

const lblLayout = document.getElementById("lblLayout");
const lblT1 = document.getElementById("lblT1");
const lblI1 = document.getElementById("lblI1");
const lblI2 = document.getElementById("lblI2");
const lblT2 = document.getElementById("lblT2");
const lblWall = document.getElementById("lblWall");
const logTableBody = document.getElementById("logTableBody");

const chkAlwaysOn = document.getElementById("chkAlwaysOn");

// Initialize and sync Side Panel with persistent background worker
document.addEventListener("DOMContentLoaded", async () => {
  // 1. Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  activeTabId = tab.id;

  // 2. Query Background service worker for capture status and log history
  chrome.runtime.sendMessage({ action: "get-status" }, (response) => {
    if (response) {
      isCapturing = response.isCapturing;
      roiCoords = response.roi;
      logCounter = response.logCounter;
      localLogs = response.logs;
      
      // Default to 240x24 ROI if not set (proportions calibrated for 1920x1080 stream)
      if (!roiCoords) {
        roiCoords = {
          x1_ratio: 0.0104,
          y1_ratio: 0.0926,
          x2_ratio: 0.1354,
          y2_ratio: 0.1148
        };
        chrome.storage.local.set({ roi: roiCoords });
        chrome.runtime.sendMessage({
          action: "calibration-locked",
          roi: roiCoords
        }).catch(() => {});
      }

      // Populate historical logs
      logTableBody.innerHTML = "";
      localLogs.forEach(log => appendLogTableRowUI(log));
      
      if (localLogs.length > 0) {
        btnExport.disabled = false;
      }
      
      if (isCapturing) {
        setUIRunning();
      } else {
        if (roiCoords) {
          btnStart.disabled = false;
          lblLayout.innerText = "Coordinates Loaded";
          lblLayout.style.color = "#e2e8f0";
        }
      }
    }
  });

  // 3. Restore alwaysOn checkbox preference
  chrome.storage.local.get(["alwaysOn"], (result) => {
    if (result.alwaysOn) {
      chkAlwaysOn.checked = true;
    }
  });

  chkAlwaysOn.addEventListener("change", () => {
    chrome.storage.local.set({ alwaysOn: chkAlwaysOn.checked });
  });

  // 4. Verify if a video player exists on the active tab DOM
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
          statusLabel.style.color = "#7f8c8d";
          btnCalibrate.disabled = false;
        }
      }
    });
  } catch (err) {
    if (!isCapturing) {
      statusDot.className = "status-dot error";
      statusLabel.innerText = "ERR: RELOAD TAB";
    }
  }
}

// Calibrate Trigger - Opens the overlay in the tab without closing the side panel
btnCalibrate.addEventListener("click", () => {
  if (!activeTabId) return;
  chrome.tabs.sendMessage(activeTabId, { action: "start-calibration" }, () => {
    lblLayout.innerText = "DRAG SELECT ROI ON TAB...";
    lblLayout.style.color = "#bfa15f";
  });
});

// Lock Calibration Coordinates inside the Side Panel UI
btnLock.addEventListener("click", () => {
  if (draftRoiCoords) {
    roiCoords = draftRoiCoords;
    chrome.storage.local.set({ roi: roiCoords }, () => {
      btnStart.disabled = false;
      lblLayout.innerText = "ROI LOCKED";
      lblLayout.style.color = "#00e676";
      
      // Reset Lock Button State
      btnLock.disabled = true;
      btnLock.style.backgroundColor = "#8a4b08";
      btnLock.style.borderColor = "#8a4b08";
      
      // Command tab to close selection overlay
      chrome.tabs.sendMessage(activeTabId, { action: "close-calibration" }).catch(() => {});
    });
  }
});

// Start Ingest
btnStart.addEventListener("click", () => {
  if (!activeTabId || !roiCoords) return;
  
  chrome.runtime.sendMessage({
    action: "start-capture",
    tabId: activeTabId,
    roi: roiCoords
  }, () => {
    setUIRunning();
  });
});

// Stop Ingest
btnStop.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "stop-capture" }, () => {
    setUIStopped();
  });
});

function setUIRunning() {
  isCapturing = true;
  btnStart.style.display = "none";
  btnStop.style.display = "block";
  btnStop.disabled = false;
  btnCalibrate.disabled = true;
  btnLock.disabled = true;
  btnExport.disabled = false;
  
  statusDot.className = "status-dot active";
  statusLabel.innerText = "INGESTING (30 FPS)";
  statusLabel.style.color = "#00e676";
  lblWall.innerText = "MONITORING ACTIVE";
  lblWall.style.color = "#00e676";
}

function setUIStopped() {
  isCapturing = false;
  btnStop.style.display = "none";
  btnStart.style.display = "block";
  btnCalibrate.disabled = false;
  
  statusDot.className = "status-dot";
  statusLabel.innerText = "ONLINE (IDLE)";
  statusLabel.style.color = "#7f8c8d";
  lblWall.innerText = "STOPPED";
  lblWall.style.color = "#7f8c8d";
}

// Listen for updates from content script & background worker
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === "update-roi") {
    roiCoords = message.roi;
    btnStart.disabled = false;
    lblLayout.innerText = "ROI LOCKED";
    lblLayout.style.color = "#00e676";
  } 
  else if (message.action === "calibration-draft") {
    draftRoiCoords = message.roi;
    // If ROI was auto-locked by content.js, also update the main roiCoords
    roiCoords = message.roi;
    btnLock.disabled = true;
    btnLock.style.backgroundColor = "#8a4b08";
    btnLock.style.borderColor = "#8a4b08";
    btnStart.disabled = false;
    lblLayout.innerText = "ROI AUTO-LOCKED";
    lblLayout.style.color = "#00e676";
  }
  else if (message.action === "frame-previews") {
    renderRawPreview(message.raw);
    
    if (message.status === "skipped") {
      lblWall.innerText = "BLOCKED: empty / transient frame";
      lblWall.style.color = "#4f5d75";
    } else if (message.status === "duplicate") {
      lblWall.innerText = "BLOCKED: duplicate event";
      lblWall.style.color = "#ff1744";
    } else if (message.status === "server_offline") {
      lblWall.innerText = "SERVER OFFLINE (127.0.0.1:5000)";
      lblWall.style.color = "#ff1744";
    } else if (message.status === "logged" && message.data) {
      lblLayout.innerText = message.data.layout;
      lblT1.innerText = message.data.t1;
      lblI1.innerText = message.data.i1;
      lblI2.innerText = message.data.i2;
      lblT2.innerText = message.data.t2;
      lblWall.innerText = "PASSED THE WALL";
      lblWall.style.color = "#00e676";
    }
  } 
  else if (message.action === "new-log-entry") {
    appendLogTableRowUI(message.log);
    btnExport.disabled = false;
  }
  else if (message.action === "tab-disconnected") {
    setUIStopped();
    lblWall.innerText = "TAB DISCONNECTED";
    lblWall.style.color = "#ff1744";
    checkVideoStatus();
  }
});

// Render base64 raw preview and binarize
function renderRawPreview(dataUrl) {
  const img = new Image();
  img.onload = () => {
    canvasRaw.width = img.width;
    canvasRaw.height = img.height;
    const ctxRaw = canvasRaw.getContext("2d");
    ctxRaw.drawImage(img, 0, 0);

    canvasBin.width = img.width;
    canvasBin.height = img.height;
    const ctxBin = canvasBin.getContext("2d");
    ctxBin.drawImage(img, 0, 0);
    const imgData = ctxBin.getImageData(0, 0, canvasBin.width, canvasBin.height);
    const data = imgData.data;
    
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

// Append log row to table UI
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
  container.scrollTop = container.scrollHeight;
}

// Export CSV logs locally
btnExport.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "get-status" }, (response) => {
    if (!response || response.logs.length === 0) return;
    
    let csvContent = "Log #,Layout Type,T1,I1,I2,T2\n";
    response.logs.forEach(log => {
      // Wrap each field in quotes to safely handle commas in player names
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
