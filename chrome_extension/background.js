let isCapturing = false;
let roiCoords = null;
let activeTabId = null;
let captureInterval = null;
let logCounter = 1;
let localLogs = [];

// Configure extension to open the Side Panel when the toolbar icon is clicked
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("Error setting side panel behavior:", error));

// Main background capture function using Promises to prevent uncaught runtime errors
async function captureTick() {
  if (!isCapturing || !activeTabId || !roiCoords) return;

  chrome.tabs.sendMessage(activeTabId, { action: "grab-frame", roi: roiCoords })
    .then(async (response) => {
      if (!response || response.error) {
        console.log("Capture stopped: frame grab failed");
        stopCapture();
        return;
      }

      const base64Jpg = response.dataUrl;
      const hasChanged = response.hasChanged;

      // 1. ALWAYS update the Side Panel raw preview for smooth 30 FPS diagnostics
      chrome.runtime.sendMessage({
        action: "frame-previews",
        raw: base64Jpg,
        status: hasChanged ? "processing" : "skipped"
      }).catch(() => {
        // Safe ignore: side panel is closed
      });

      // 2. ONLY POST to server if the browser-side pixel diff gate detected a change
      if (!hasChanged) return;

      try {
        const res = await fetch("http://127.0.0.1:5000/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: base64Jpg })
        });
        
        if (res.ok) {
          const result = await res.json();
          
          if (result.status === "duplicate") {
            chrome.runtime.sendMessage({
              action: "frame-previews",
              raw: base64Jpg,
              status: "duplicate"
            }).catch(() => {});
            return;
          }

          if (result.status === "logged" && result.data) {
            const logData = {
              log_num: logCounter,
              layout: result.data.layout,
              t1: result.data.t1,
              i1: result.data.i1,
              i2: result.data.i2,
              t2: result.data.t2
            };
            
            localLogs.push(logData);
            logCounter++;

            // Update previews with the parsed data
            chrome.runtime.sendMessage({
              action: "frame-previews",
              raw: base64Jpg,
              status: "logged",
              data: result.data
            }).catch(() => {});

            // Broadcast the new log to Side Panel
            chrome.runtime.sendMessage({
              action: "new-log-entry",
              log: logData
            }).catch(() => {});
          }
        }
      } catch (err) {
        console.log("Error sending frame to server:", err);
        chrome.runtime.sendMessage({
          action: "frame-previews",
          raw: base64Jpg,
          status: "server_offline"
        }).catch(() => {});
      }
    })
    .catch((err) => {
      console.log("Communication lost with stream tab:", err.message);
      stopCapture();
      
      // Notify UI that the connection was severed
      chrome.runtime.sendMessage({
        action: "tab-disconnected"
      }).catch(() => {});
    });
}

function startCapture(tabId, roi) {
  if (isCapturing) return;
  isCapturing = true;
  activeTabId = tabId;
  roiCoords = roi;
  // V1.1: 30 FPS (33ms interval) — Stage 1 pixel diff gate handles OCR rate
  captureInterval = setInterval(captureTick, 33);
}

function stopCapture() {
  isCapturing = false;
  if (captureInterval) {
    clearInterval(captureInterval);
    captureInterval = null;
  }
}

// Coordinate message router
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "calibration-locked") {
    chrome.runtime.sendMessage({
      action: "update-roi",
      roi: message.roi
    }).catch(() => {});
    sendResponse({ status: "ok" });
  } 
  else if (message.action === "start-capture") {
    startCapture(message.tabId, message.roi);
    sendResponse({ status: "started" });
  } 
  else if (message.action === "auto-start-capture") {
    startCapture(sender.tab.id, message.roi);
    sendResponse({ status: "started_auto" });
  }
  else if (message.action === "stop-capture") {
    stopCapture();
    sendResponse({ status: "stopped" });
  } 
  else if (message.action === "get-status") {
    sendResponse({
      isCapturing: isCapturing,
      roi: roiCoords,
      tabId: activeTabId,
      logs: localLogs,
      logCounter: logCounter
    });
  }
  return true;
});
