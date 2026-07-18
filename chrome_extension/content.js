/**
 * FragEngine V0.14 — Content Script
 * 
 * V0.14 Architecture Change:
 * - Removed fixed 30FPS capture loop
 * - grabFrame() now returns ImageData alongside dataUrl for feed detection
 * - SamplingEngine controls when frames are captured
 * - Calibration overlay with auto-lock on mouseup
 */

let videoElement = null;
let overlayDiv = null;
let selectCanvas = null;

let startX = 0, startY = 0;
let isDragging = false;
let currentCalibrationTarget = "t1";
let roiCoords = {
  t1: null,
  t2: null,
  icons: null
};

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

    roiCoords[currentCalibrationTarget] = {
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
      target: currentCalibrationTarget,
      roi: roiCoords
    }).catch(() => {});
    
    chrome.runtime.sendMessage({
      action: "calibration-draft",
      target: currentCalibrationTarget,
      roi: roiCoords
    }).catch(() => {});
    
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

  // Fallback if not fully calibrated yet
  if (!roi || !roi.t1 || !roi.t2 || !roi.icons) {
    return { error: "Awaiting 3-ROI Calibration" };
  }

  // Calc crop dims for t1, t2, icons
  const parseROI = (subRoi) => {
    const x1 = Math.floor(subRoi.x1_ratio * vidW);
    const y1 = Math.floor(subRoi.y1_ratio * vidH);
    const x2 = Math.floor(subRoi.x2_ratio * vidW);
    const y2 = Math.floor(subRoi.y2_ratio * vidH);
    return { x1, y1, x2, y2, w: x2 - x1, h: y2 - y1 };
  };

  const t1 = parseROI(roi.t1);
  const t2 = parseROI(roi.t2);
  const icons = parseROI(roi.icons);

  if (t1.w <= 0 || t1.h <= 0 || t2.w <= 0 || t2.h <= 0 || icons.w <= 0 || icons.h <= 0) {
    return { error: "Invalid crop dimensions" };
  }

  // Row height slice offsets
  const rowH_t1 = Math.floor(t1.h / 4);
  const rowH_t2 = Math.floor(t2.h / 4);
  const rowH_icons = Math.floor(icons.h / 4);

  const segments = [];
  if (!window.prevSegmentsGray) {
    window.prevSegmentsGray = [null, null, null, null];
  }

  for (let s = 0; s < 4; s++) {
    // 1. Crop T1 segment
    const t1Canvas = document.createElement("canvas");
    t1Canvas.width = t1.w;
    t1Canvas.height = rowH_t1;
    const t1Ctx = t1Canvas.getContext("2d");
    t1Ctx.drawImage(videoElement, t1.x1, t1.y1 + s * rowH_t1, t1.w, rowH_t1, 0, 0, t1.w, rowH_t1);
    const t1DataUrl = t1Canvas.toDataURL("image/jpeg", 0.90);
    const t1ImgData = t1Ctx.getImageData(0, 0, t1.w, rowH_t1);

    // 2. Crop T2 segment
    const t2Canvas = document.createElement("canvas");
    t2Canvas.width = t2.w;
    t2Canvas.height = rowH_t2;
    const t2Ctx = t2Canvas.getContext("2d");
    t2Ctx.drawImage(videoElement, t2.x1, t2.y1 + s * rowH_t2, t2.w, rowH_t2, 0, 0, t2.w, rowH_t2);
    const t2DataUrl = t2Canvas.toDataURL("image/jpeg", 0.90);
    const t2ImgData = t2Ctx.getImageData(0, 0, t2.w, rowH_t2);

    // 3. Crop Icons segment
    const iconCanvas = document.createElement("canvas");
    iconCanvas.width = icons.w;
    iconCanvas.height = rowH_icons;
    const iconCtx = iconCanvas.getContext("2d");
    iconCtx.drawImage(videoElement, icons.x1, icons.y1 + s * rowH_icons, icons.w, rowH_icons, 0, 0, icons.w, rowH_icons);
    const iconDataUrl = iconCanvas.toDataURL("image/jpeg", 0.90);
    const iconImgData = iconCtx.getImageData(0, 0, icons.w, rowH_icons);

    // Grayscale convert for pixel diff check on Icon crop
    const pixels = iconImgData.data;
    const len = pixels.length;
    const currentGray = new Uint8Array(len / 4);
    let idx = 0;
    for (let i = 0; i < len; i += 4) {
      currentGray[idx++] = Math.round(0.299 * pixels[i] + 0.587 * pixels[i+1] + 0.114 * pixels[i+2]);
    }

    let hasChanged = false;
    let meanDiff = 0;
    const prevSubGray = window.prevSegmentsGray[s];

    if (!prevSubGray || prevSubGray.length !== currentGray.length) {
      hasChanged = true;
      meanDiff = 255;
    } else {
      let sumDiff = 0;
      const numPixels = currentGray.length;
      for (let i = 0; i < numPixels; i++) {
        sumDiff += Math.abs(currentGray[i] - prevSubGray[i]);
      }
      meanDiff = sumDiff / numPixels;
      if (meanDiff >= 8.0) {
        hasChanged = true;
      }
    }

    window.prevSegmentsGray[s] = currentGray;

    segments.push({
      rowIndex: s,
      t1_dataUrl: t1DataUrl,
      t1_imageData: t1ImgData,
      t2_dataUrl: t2DataUrl,
      t2_imageData: t2ImgData,
      icon_dataUrl: iconDataUrl,
      icon_imageData: iconImgData,
      hasChanged: hasChanged,
      meanDiff: Math.round(meanDiff * 100) / 100
    });
  }

  // Return diagnostic preview (using icons canvas as raw frame preview)
  const previewCanvas = document.createElement("canvas");
  previewCanvas.width = icons.w;
  previewCanvas.height = icons.h;
  const prevCtx = previewCanvas.getContext("2d");
  prevCtx.drawImage(videoElement, icons.x1, icons.y1, icons.w, icons.h, 0, 0, icons.w, icons.h);
  const dataUrl = previewCanvas.toDataURL("image/jpeg", 0.90);
  const imageData = prevCtx.getImageData(0, 0, icons.w, icons.h);

  return { dataUrl, imageData, hasChanged: segments.some(s => s.hasChanged), meanDiff: segments[0].meanDiff, segments };
}

// Initialize Sampling Engine with references to our functions
SamplingEngine.init(grabFrame, getROI);

// Message Listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "detect-video") {
    const hasVideo = !!findVideo();
    sendResponse({ hasVideo: hasVideo });
  } 
  else if (message.action === "start-calibration") {
    currentCalibrationTarget = message.target || "t1";
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
