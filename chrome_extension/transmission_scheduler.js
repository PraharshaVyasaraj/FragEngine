/**
 * FragEngine V0.14 — Transmission Scheduler
 * Controls WHEN frames are sent to the Flask backend.
 * 
 * During Rapid mode, the sampling engine evaluates frames every 200ms.
 * But we only SEND the latest frame every 800ms.
 * This means 4 samples arrive per send window — we discard the first 3
 * and send the 4th (the clearest, most stable frame).
 */

const TransmissionScheduler = (() => {
  const SEND_INTERVAL_MS = 800;

  let lastSendTime = 0;
  let latestFrame = null;
  let pendingSend = false;
  let sendTimer = null;

  // Diagnostics
  let stats = {
    framesSent: 0,
    framesRejected: 0,
    lastSendTimestamp: null,
    nextSendIn: 0
  };

  /**
   * Evaluate a frame for transmission.
   * Called every 200ms during Rapid mode.
   * @param {Object} frame — { dataUrl, imageData, hasChanged }
   */
  function evaluate(frame) {
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

  return { evaluate, reset, getDiagnostics };
})();
