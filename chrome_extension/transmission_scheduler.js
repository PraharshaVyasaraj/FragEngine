/**
 * FragEngine V0.14 — Transmission Scheduler
 * Controls WHEN frames are sent to the Flask backend.
 * 
 * During Rapid mode, the sampling engine evaluates frames every 200ms.
 * But we only SEND the latest frame every 360ms.
 * This means 2 samples arrive per send window.
 */

const TransmissionScheduler = (() => {
  const SEND_INTERVAL_MS = 360;

  let lastSendTime = 0;
  let latestFrame = null;
  let pendingSend = false;
  let sendTimer = null;
  let lastSentImageData = null;

  // Diagnostics
  let stats = {
    framesSent: 0,
    framesRejected: 0,
    lastSendTimestamp: null,
    nextSendIn: 0
  };

  /**
   * Compare grayscale binarized similarity of two frames.
   */
  function isSimilarFrame(imgData1, imgData2) {
    if (!imgData1 || !imgData2) return false;
    if (imgData1.width !== imgData2.width || imgData1.height !== imgData2.height) return false;

    const data1 = imgData1.data;
    const data2 = imgData2.data;
    const len = data1.length;
    let matchingPixels = 0;
    const totalPixels = len / 4;

    for (let i = 0; i < len; i += 4) {
      const gray1 = 0.299 * data1[i] + 0.587 * data1[i+1] + 0.114 * data1[i+2];
      const bin1 = gray1 >= 180 ? 1 : 0;

      const gray2 = 0.299 * data2[i] + 0.587 * data2[i+1] + 0.114 * data2[i+2];
      const bin2 = gray2 >= 180 ? 1 : 0;

      if (bin1 === bin2) {
        matchingPixels++;
      }
    }

    const similarity = matchingPixels / totalPixels;
    return similarity >= 0.95;
  }

  /**
   * Evaluate a frame for transmission.
   * Called every 200ms during Rapid mode.
   * @param {Object} frame — { dataUrl, imageData, hasChanged }
   */
  function evaluate(frame) {
    // Client-side similarity suppression (V0.14.3)
    if (lastSentImageData && frame.imageData) {
      if (isSimilarFrame(frame.imageData, lastSentImageData)) {
        stats.framesRejected++;
        return; // Suppress duplicate
      }
    }

    latestFrame = frame;
    const now = Date.now();
    const elapsed = now - lastSendTime;

    if (elapsed >= SEND_INTERVAL_MS) {
      // Send immediately
      send();
    } else {
      // Schedule send at end of window if not already scheduled
      stats.framesRejected++;
      stats.nextSendIn = SEND_INTERVAL_MS - elapsed;
      
      if (!pendingSend) {
        pendingSend = true;
        sendTimer = setTimeout(() => {
          send();
          pendingSend = false;
        }, SEND_INTERVAL_MS - elapsed);
      }
    }
  }

  /**
   * Send the latest frame to the Flask backend.
   */
  function send() {
    if (!latestFrame) return;

    const frame = latestFrame;
    latestFrame = null;
    lastSendTime = Date.now();
    stats.framesSent++;
    stats.lastSendTimestamp = new Date().toISOString();
    stats.nextSendIn = SEND_INTERVAL_MS;

    // Cache binarized mask of the sent frame
    if (frame.imageData) {
      lastSentImageData = new ImageData(
        new Uint8ClampedArray(frame.imageData.data),
        frame.imageData.width,
        frame.imageData.height
      );
    }

    // Send to background worker for server POST
    chrome.runtime.sendMessage({
      action: "send-frame",
      dataUrl: frame.dataUrl
    }).catch(() => {});
  }

  /**
   * Reset scheduler state (called when capture stops).
   */
  function reset() {
    lastSendTime = 0;
    latestFrame = null;
    pendingSend = false;
    lastSentImageData = null;
    if (sendTimer) {
      clearTimeout(sendTimer);
      sendTimer = null;
    }
    stats = {
      framesSent: 0,
      framesRejected: 0,
      lastSendTimestamp: null,
      nextSendIn: 0
    };
  }

  /**
   * Get scheduler diagnostics.
   */
  function getDiagnostics() {
    const now = Date.now();
    const elapsed = now - lastSendTime;
    return {
      ...stats,
      nextSendIn: Math.max(0, SEND_INTERVAL_MS - elapsed),
      sendIntervalMs: SEND_INTERVAL_MS
    };
  }

  return { evaluate, enqueue: evaluate, reset, getDiagnostics };
})();
