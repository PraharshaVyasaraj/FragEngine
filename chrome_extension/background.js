let isCapturing = false;
let roiCoords = null;
let activeTabId = null;
let logCounter = 1;
let localLogs = [];
let isIgnoring = false;

// Configure extension to open the Side Panel when the toolbar icon is clicked
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("Error setting side panel behavior:", error));

/**
 * Handle sending frame to backend server (called from content script Scheduler).
 */
async function sendFrameToServer(base64Jpg, rowIndex) {
  if (!isCapturing || isIgnoring) return;

  try {
    const res = await fetch("http://127.0.0.1:5000/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64Jpg, row_index: rowIndex })
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
}

function startCapture(tabId, roi) {
  if (isCapturing) return;
  isCapturing = true;
  activeTabId = tabId;
  roiCoords = roi;
  
  // Command active tab to start its sampling engine
  chrome.tabs.sendMessage(activeTabId, { action: "start-sampling", roi: roiCoords }).catch((err) => {
    console.error("Failed to start sampling in tab:", err);
    stopCapture();
  });
}

function stopCapture() {
  if (!isCapturing) return;
  isCapturing = false;
  if (activeTabId) {
    chrome.tabs.sendMessage(activeTabId, { action: "stop-sampling" }).catch(() => {});
  }
}

// Message router
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "calibration-locked") {
    roiCoords = message.roi;
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
  else if (message.action === "send-frame") {
    sendFrameToServer(message.dataUrl, message.rowIndex);
    sendResponse({ status: "sending" });
  }
  else if (message.action === "get-status") {
    sendResponse({
      isCapturing: isCapturing,
      roi: roiCoords,
      tabId: activeTabId,
      logs: localLogs,
      logCounter: logCounter,
      isIgnoring: isIgnoring
    });
  }
  else if (message.action === "toggle-ignore") {
    isIgnoring = !isIgnoring;
    sendResponse({ isIgnoring: isIgnoring });
  }
  return true;
});
