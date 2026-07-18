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

  let lastSendTimes = [0, 0, 0, 0];
  let lastSentSegments = [null, null, null, null];

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
   * Evaluate a frame's segments for transmission.
   * @param {Object} frame — { dataUrl, imageData, hasChanged, segments }
   */
  function evaluate(frame) {
    if (!frame.segments) return;
    
    const now = Date.now();
    
    frame.segments.forEach((segment, s) => {
      // 1. Gating check: has this specific row changed?
      if (!segment.hasChanged) return;
      
      // 2. Feed icon presence check on this segment
      const feedPresent = FeedDetector.detect(segment.imageData);
      if (!feedPresent) return;
      
      // 3. Client-side similarity suppression
      const lastSent = lastSentSegments[s];
      if (lastSent && isSimilarFrame(segment.imageData, lastSent)) {
        stats.framesRejected++;
        return;
      }
      
      // 4. Rate-limit check per row
      const elapsed = now - lastSendTimes[s];
      if (elapsed >= SEND_INTERVAL_MS) {
        lastSendTimes[s] = now;
        stats.framesSent++;
        stats.lastSendTimestamp = new Date().toISOString();
        
        lastSentSegments[s] = new ImageData(
          new Uint8ClampedArray(segment.imageData.data),
          segment.imageData.width,
          segment.imageData.height
        );
        
        chrome.runtime.sendMessage({
          action: "send-frame",
          dataUrl: segment.dataUrl,
          rowIndex: s
        }).catch(() => {});
      } else {
        stats.framesRejected++;
      }
    });
  }

  /**
   * Reset scheduler state (called when capture stops).
   */
  function reset() {
    lastSendTimes = [0, 0, 0, 0];
    lastSentSegments = [null, null, null, null];
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

  return { evaluate, reset, getDiagnostics };
})();
