/**
 * FragEngine V0.16 — Sampling Engine
 * Standard constant 300ms sampling rate with no modes.
 */

const SamplingEngine = (() => {
  const INTERVAL_MS = 300;

  let mode = 'IDLE';  // 'IDLE', 'RUNNING'
  let intervalId = null;
  let sessionStartTime = null;
  let stats = {
    framesSampled: 0,
    framesWithIcon: 0,
  };

  let grabFrameFn = null;
  let roiCoordsFn = null;

  /**
   * Initialize the sampling engine.
   * @param {Function} grabFrame — function(roi) from content.js
   * @param {Function} getRoi — function() returning current roiCoords
   */
  function init(grabFrame, getRoi) {
    grabFrameFn = grabFrame;
    roiCoordsFn = getRoi;
  }

  /**
   * Start the sampling engine.
   */
  function start() {
    if (mode !== 'IDLE') return;
    sessionStartTime = Date.now();
    stats = {
      framesSampled: 0,
      framesWithIcon: 0,
    };
    TransmissionScheduler.reset();
    mode = 'RUNNING';
    intervalId = setInterval(sampleAndDetect, INTERVAL_MS);
    broadcastModeChange('RUNNING');
  }

  /**
   * Stop the sampling engine.
   */
  function stop() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    mode = 'IDLE';
    broadcastModeChange('IDLE');
  }

  /**
   * Core sample-and-detect loop running at steady 300ms interval.
   */
  function sampleAndDetect() {
    if (!grabFrameFn || !roiCoordsFn) return;
    
    const roi = roiCoordsFn();
    if (!roi) return;
    
    const frame = grabFrameFn(roi);
    if (!frame || frame.error) return;

    stats.framesSampled++;

    // Evaluate segments for transmission
    TransmissionScheduler.evaluate(frame);

    // Broadcast frame preview to side panel
    chrome.runtime.sendMessage({
      action: "frame-previews",
      raw: frame.dataUrl,
      status: "monitoring",
      diagnostics: {
        mode: mode,
        pixelDiff: frame.meanDiff || 0,
        feedDetector: FeedDetector.getDiagnostics(),
        scheduler: TransmissionScheduler.getDiagnostics(),
        engine: getDiagnostics()
      }
    }).catch(() => {});
  }

  function broadcastModeChange(newMode) {
    chrome.runtime.sendMessage({
      action: "mode-change",
      mode: newMode,
      timestamp: new Date().toISOString()
    }).catch(() => {});
  }

  /**
   * Get engine diagnostics.
   */
  function getDiagnostics() {
    const now = Date.now();
    const sessionDuration = sessionStartTime ? (now - sessionStartTime) / 1000 : 0;
    
    return {
      mode,
      framesSampled: stats.framesSampled,
      framesWithIcon: stats.framesWithIcon,
      sessionDurationSec: Math.round(sessionDuration),
      currentIntervalMs: INTERVAL_MS
    };
  }

  return { init, start, stop, getDiagnostics };
})();
