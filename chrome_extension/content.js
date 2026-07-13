let videoElement = null;
let overlayDiv = null;
let selectCanvas = null;

let startX = 0, startY = 0;
let isDragging = false;
let roiCoords = null; // Proportional coordinates

function findVideo() {
  return document.querySelector("video");
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
    
    roiCoords = {
      x1_ratio: x1 / selectCanvas.width,
      y1_ratio: y1 / selectCanvas.height,
      x2_ratio: x2 / selectCanvas.width,
      y2_ratio: y2 / selectCanvas.height
    };
    
    // Send draft coordinates to Side Panel in real-time
    chrome.runtime.sendMessage({
      action: "calibration-draft",
      roi: roiCoords
    }).catch(() => {});
    
    // Grab a single preview frame and send it so it renders inside the Side Panel immediately!
    const frameRes = grabFrame(roiCoords);
    if (frameRes && !frameRes.error) {
      chrome.runtime.sendMessage({
        action: "frame-previews",
        raw: frameRes.dataUrl,
        status: "skipped" // skipped means no database write, just a preview
      }).catch(() => {});
    }
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

let prevFrameGray = null;

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
  const ctx = canvas.getContext("2d");
  
  ctx.drawImage(videoElement, vx1, vy1, cropW, cropH, 0, 0, cropW, cropH);
  
  const imgData = ctx.getImageData(0, 0, cropW, cropH);
  const pixels = imgData.data;
  
  // Convert current frame to grayscale
  const len = pixels.length;
  const currentGray = new Uint8Array(len / 4);
  let idx = 0;
  for (let i = 0; i < len; i += 4) {
    currentGray[idx++] = Math.round(0.299 * pixels[i] + 0.587 * pixels[i+1] + 0.114 * pixels[i+2]);
  }
  
  let hasChanged = false;
  if (!prevFrameGray || prevFrameGray.length !== currentGray.length) {
    hasChanged = true;
  } else {
    let sumDiff = 0;
    const numPixels = currentGray.length;
    for (let i = 0; i < numPixels; i++) {
      sumDiff += Math.abs(currentGray[i] - prevFrameGray[i]);
    }
    const meanDiff = sumDiff / numPixels;
    if (meanDiff >= 8.0) { // Keep same 8.0 threshold as V1.1
      hasChanged = true;
    }
  }
  
  prevFrameGray = currentGray;
  
  const dataUrl = canvas.toDataURL("image/jpeg", 0.90);
  return { dataUrl: dataUrl, hasChanged: hasChanged };
}

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
  return true;
});

// Auto-start capture if "alwaysOn" is enabled
function checkAutoStart() {
  const video = findVideo();
  if (video) {
    chrome.storage.local.get(["roi", "alwaysOn"], (result) => {
      if (result.alwaysOn && result.roi) {
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
