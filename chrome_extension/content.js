/**
 * FragEngine V0.16.1 — Content Script
 *
 * V0.16.1 Changes:
 * - ROI auto-loaded from chrome.storage.local on page load
 * - toggle-overlay message handler for Alt+Shift+V keyboard shortcut
 * - scale profile read from storage and passed to server on each send-frame
 */

let videoElement = null;
let overlayDiv = null;
let selectCanvas = null;

let startX = 0, startY = 0;
let isDragging = false;
let roiCoords = null; // Proportional coordinates

let prevFrameGray = null;

function findVideo() {
  return document.querySelector("video");
}

function getROI() {
  return roiCoords;
}

function startCalibration() {
  videoElement = findVideo();
  if (!videoElement) {
    alert("Error: No active <video> stream detected on this page.");
    return;
  }
  
  // Disable body scroll while calibrating
  document.body.style.overflow = "hidden";
  
  removeCalibrationOverlay();
  
  const rect = videoElement.getBoundingClientRect();
  
  // Create overlay container
  overlayDiv = document.createElement("div");
  overlayDiv.style.position = "absolute";
  overlayDiv.style.top = `${rect.top + window.scrollY}px`;
  overlayDiv.style.left = `${rect.left + window.scrollX}px`;
  overlayDiv.style.width = `${rect.width}px`;
  overlayDiv.style.height = `${rect.height}px`;
  overlayDiv.style.zIndex = "2147483647";
  overlayDiv.style.cursor = "crosshair";
  overlayDiv.style.backgroundColor = "rgba(0,0,0,0.3)";
  overlayDiv.style.boxSizing = "border-box";
  overlayDiv.style.border = "2px dashed #bfa15f";
  
  selectCanvas = document.createElement("canvas");
  selectCanvas.width = rect.width;
  selectCanvas.height = rect.height;
  selectCanvas.style.width = "100%";
  selectCanvas.style.height = "100%";
  overlayDiv.appendChild(selectCanvas);
  
  const ctx = selectCanvas.getContext("2d");
  
  selectCanvas.addEventListener("mousedown", (e) => {
    const r = selectCanvas.getBoundingClientRect();
    startX = e.clientX - r.left;
    startY = e.clientY - r.top;
    isDragging = true;
  });
  
  selectCanvas.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const r = selectCanvas.getBoundingClientRect();
    const curX = e.clientX - r.left;
    const curY = e.clientY - r.top;
    
    ctx.clearRect(0, 0, selectCanvas.width, selectCanvas.height);
    
    const x = Math.min(startX, curX);
    const y = Math.min(startY, curY);
    const w = Math.abs(startX - curX);
    const h = Math.abs(startY - curY);
    
    ctx.strokeStyle = "#d35400"; // Tactical copper selection
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    
    // Draw crosshair grid ticks
    ctx.strokeStyle = "rgba(191, 161, 95, 0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y + h/2);
    ctx.lineTo(x + w, y + h/2);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(x + w/2, y);
    ctx.lineTo(x + w/2, y + h);
    ctx.stroke();
    
    // Resolution badge
    ctx.fillStyle = "#1d212a";
    ctx.fillRect(x + 5, y + 5, 85, 18);
    ctx.strokeStyle = "#4f5d75";
    ctx.strokeRect(x + 5, y + 5, 85, 18);
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "10px monospace";
    ctx.fillText(`[${Math.round(w)}px x ${Math.round(h)}px]`, x + 10, y + 17);
  });
  
  selectCanvas.addEventListener("mouseup", (e) => {
    if (!isDragging) return;
    isDragging = false;
    const r = selectCanvas.getBoundingClientRect();
    const curX = e.clientX - r.left;
    const curY = e.clientY - r.top;
    
    let x1 = Math.min(startX, curX);
    let y1 = Math.min(startY, curY);
    let x2 = Math.max(startX, curX);
    let y2 = Math.max(startY, curY);
    
    // If the drag area is too small (e.g. a single click), auto-create a 240x24 box centered on the click
    if ((x2 - x1) <= 10 || (y2 - y1) <= 10) {
      x1 = Math.max(0, startX - 120);
      y1 = Math.max(0, startY - 12);
      x2 = Math.min(selectCanvas.width, startX + 120);
      y2 = Math.min(selectCanvas.height, startY + 12);
    }
    
    // Apply V0.14.3 horizontal buffer margin (+20px) to prevent player name clipping
    x1 = Math.max(0, x1 - 20);
    x2 = Math.min(selectCanvas.width, x2 + 20);

    roiCoords = {
      x1_ratio: x1 / selectCanvas.width,
      y1_ratio: y1 / selectCanvas.height,
      x2_ratio: x2 / selectCanvas.width,
      y2_ratio: y2 / selectCanvas.height
    };
    
    // AUTO-LOCK: Persist ROI to storage immediately
    chrome.storage.local.set({ roi: roiCoords });
    
    // Notify background worker and side panel
    chrome.runtime.sendMessage({
      action: "calibration-locked",
      roi: roiCoords
    }).catch(() => {});
    
    chrome.runtime.sendMessage({
      action: "calibration-draft",
      roi: roiCoords
    }).catch(() => {});
    
    // Preview frame
    const frameRes = grabFrame(roiCoords);
    if (frameRes && !frameRes.error) {
      chrome.runtime.sendMessage({
        action: "frame-previews",
        raw: frameRes.dataUrl,
        status: "skipped"
      }).catch(() => {});
    }
    
    // Auto-close overlay
    setTimeout(() => removeCalibrationOverlay(), 300);
  });
  
  document.body.appendChild(overlayDiv);
}

function removeCalibrationOverlay() {
  if (overlayDiv) {
    overlayDiv.remove();
    overlayDiv = null;
    selectCanvas = null;
  }
  document.body.style.overflow = "";
}

/**
 * Grab a single frame from the video element at the specified ROI.
 * V0.14: Now returns ImageData for FeedDetector alongside dataUrl and pixel diff.
 * 
 * @param {Object} roi — { x1_ratio, y1_ratio, x2_ratio, y2_ratio }
 * @returns {Object} { dataUrl, imageData, hasChanged, meanDiff }
 */
function grabFrame(roi) {
  videoElement = findVideo();
  if (!videoElement) {
    return { error: "No video player element" };
  }
  
  const vidW = videoElement.videoWidth;
  const vidH = videoElement.videoHeight;
  
  if (vidW === 0 || vidH === 0) {
    return { error: "Video stream has no dimensions" };
  }
  
  const vx1 = Math.floor(roi.x1_ratio * vidW);
  const vy1 = Math.floor(roi.y1_ratio * vidH);
  const vx2 = Math.floor(roi.x2_ratio * vidW);
  const vy2 = Math.floor(roi.y2_ratio * vidH);
  
  const cropW = vx2 - vx1;
  const cropH = vy2 - vy1;
  
  if (cropW <= 0 || cropH <= 0) {
    return { error: "Invalid crop dimensions" };
  }
  
  const canvas = document.createElement("canvas");
  canvas.width = cropW;
  canvas.height = cropH;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  
  ctx.drawImage(videoElement, vx1, vy1, cropW, cropH, 0, 0, cropW, cropH);
  
  // Get ImageData for FeedDetector (V0.14)
  const imageData = ctx.getImageData(0, 0, cropW, cropH);
  const pixels = imageData.data;
  
  // Convert current frame to grayscale for pixel diff
  const len = pixels.length;
  const currentGray = new Uint8Array(len / 4);
  let idx = 0;
  for (let i = 0; i < len; i += 4) {
    currentGray[idx++] = Math.round(0.299 * pixels[i] + 0.587 * pixels[i+1] + 0.114 * pixels[i+2]);
  }
  
  let hasChanged = false;
  let meanDiff = 0;
  if (!prevFrameGray || prevFrameGray.length !== currentGray.length) {
    hasChanged = true;
    meanDiff = 255; // First frame always counts as changed
  } else {
    let sumDiff = 0;
    const numPixels = currentGray.length;
    for (let i = 0; i < numPixels; i++) {
      sumDiff += Math.abs(currentGray[i] - prevFrameGray[i]);
    }
    meanDiff = sumDiff / numPixels;
    if (meanDiff >= 8.0) {
      hasChanged = true;
    }
  }
  
  prevFrameGray = currentGray;
  
  const dataUrl = canvas.toDataURL("image/jpeg", 0.90);
  return { dataUrl, imageData, hasChanged, meanDiff: Math.round(meanDiff * 100) / 100 };
}

// Auto-restore ROI from persistent storage on page load
chrome.storage.local.get(["roi"], (result) => {
  if (result.roi) {
    roiCoords = result.roi;
  }
});

// Initialize Sampling Engine with references to our functions
SamplingEngine.init(grabFrame, getROI);

// Message Listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "detect-video") {
    const hasVideo = !!findVideo();
    sendResponse({ hasVideo: hasVideo });
  } 
  else if (message.action === "start-calibration") {
    startCalibration();
    sendResponse({ status: "overlay_launched" });
  } 
  else if (message.action === "close-calibration") {
    removeCalibrationOverlay();
    sendResponse({ status: "overlay_closed" });
  }
  else if (message.action === "grab-frame") {
    const res = grabFrame(message.roi);
    sendResponse(res);
  }
  else if (message.action === "start-sampling") {
    // V0.14: Start the sampling engine (Normal mode)
    if (message.roi) {
      roiCoords = message.roi;
    }
    SamplingEngine.start();
    sendResponse({ status: "sampling_started" });
  }
  else if (message.action === "stop-sampling") {
    SamplingEngine.stop();
    prevFrameGray = null;
    sendResponse({ status: "sampling_stopped" });
  }
  else if (message.action === "get-diagnostics") {
    sendResponse({
      engine: SamplingEngine.getDiagnostics(),
      detector: FeedDetector.getDiagnostics(),
      scheduler: TransmissionScheduler.getDiagnostics()
    });
  }
  else if (message.action === "toggle-overlay") {
    // Toggle the in-page Cyber-Red HUD overlay visibility (Alt+Shift+V)
    const overlay = document.getElementById("fragengine-inpage-overlay");
    if (overlay) {
      overlay.style.display = overlay.style.display === "none" ? "block" : "none";
    }
    sendResponse({ status: "toggled" });
  }
  else if (message.action === "toggle-roundabout") {
    // Toggle the Smart Roundabout App Dock (Alt+Shift+R)
    const roundabout = document.getElementById("fragengine-roundabout-root");
    if (roundabout) {
      roundabout.style.display = roundabout.style.display === "none" ? "block" : "none";
    }
    sendResponse({ status: "toggled" });
  }
  return true;
});

// Auto-start if alwaysOn
function checkAutoStart() {
  const video = findVideo();
  if (video) {
    chrome.storage.local.get(["roi", "alwaysOn"], (result) => {
      if (result.alwaysOn && result.roi) {
        roiCoords = result.roi;
        SamplingEngine.start();
        chrome.runtime.sendMessage({
          action: "auto-start-capture",
          roi: result.roi
        }).catch(() => {});
      }
    });
  } else {
    let retries = 0;
    const interval = setInterval(() => {
      const v = findVideo();
      if (v) {
        clearInterval(interval);
        chrome.storage.local.get(["roi", "alwaysOn"], (result) => {
          if (result.alwaysOn && result.roi) {
            roiCoords = result.roi;
            SamplingEngine.start();
            chrome.runtime.sendMessage({
              action: "auto-start-capture",
              roi: result.roi
            }).catch(() => {});
          }
        });
      }
      retries++;
      if (retries > 10) clearInterval(interval);
    }, 1000);
  }
}

checkAutoStart();
