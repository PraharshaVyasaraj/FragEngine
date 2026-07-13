/**
 * FragEngine V0.14 — Sampling Engine
 * Adaptive Normal/Rapid state machine.
 * 
 * NORMAL MODE: Sample every 700ms. Low CPU. Detect if kill feed icon appears.
 * RAPID MODE:  Sample every 200ms. Track feed. Send frames via TransmissionScheduler.
 * 
 * Transition:
 *   Normal → Rapid:  When FeedDetector.detect() returns true
 *   Rapid → Normal:  2 seconds after last icon detection (cooldown)
 */

const SamplingEngine = (() => {
  const NORMAL_INTERVAL_MS = 700;
  const RAPID_INTERVAL_MS = 200;
  const RAPID_COOLDOWN_MS = 2000; // Stay rapid for 2s after last icon

  let mode = 'IDLE';  // 'IDLE', 'NORMAL', 'RAPID'
  let intervalId = null;
  let cooldownTimer = null;
  let lastIconDetectedTime = 0;

  // Session stats
  let sessionStartTime = null;
  let stats = {
    framesSampled: 0,
    framesWithIcon: 0,
    normalModeTime: 0,
    rapidModeTime: 0,
    modeTransitions: 0,
    lastModeChange: null
  };

  let modeStartTime = null;

  // Reference to content.js functions (set during init)
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
   * Start the sampling engine in Normal mode.
   */
  function start() {
    if (mode !== 'IDLE') return;
    sessionStartTime = Date.now();
    modeStartTime = Date.now();
    stats = {
      framesSampled: 0,
      framesWithIcon: 0,
      normalModeTime: 0,
      rapidModeTime: 0,
      modeTransitions: 0,
      lastModeChange: null
    };
    TransmissionScheduler.reset();
    enterNormalMode();
  }

  /**
   * Stop the sampling engine.
   */
  function stop() {
    // Accumulate time for current mode
    if (modeStartTime) {
      const elapsed = Date.now() - modeStartTime;
      if (mode === 'NORMAL') stats.normalModeTime += elapsed;
      else if (mode === 'RAPID') stats.rapidModeTime += elapsed;
    }
    
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    if (cooldownTimer) {
      clearTimeout(cooldownTimer);
      cooldownTimer = null;
    }
    mode = 'IDLE';
  }

  function enterNormalMode() {
    // Accumulate rapid time if switching from rapid
    if (mode === 'RAPID' && modeStartTime) {
      stats.rapidModeTime += Date.now() - modeStartTime;
    }
    
    mode = 'NORMAL';
    modeStartTime = Date.now();
    
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(sampleAndDetect, NORMAL_INTERVAL_MS);
    
    if (cooldownTimer) {
      clearTimeout(cooldownTimer);
      cooldownTimer = null;
    }

    broadcastModeChange('NORMAL');
  }

  function enterRapidMode() {
    // Accumulate normal time if switching from normal
    if (mode === 'NORMAL' && modeStartTime) {
      stats.normalModeTime += Date.now() - modeStartTime;
    }
    
    if (mode !== 'RAPID') {
      stats.modeTransitions++;
      stats.lastModeChange = new Date().toISOString();
    }
    
    mode = 'RAPID';
    modeStartTime = Date.now();
    
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(sampleAndDetect, RAPID_INTERVAL_MS);
    
    // Clear any pending normal-return cooldown
    if (cooldownTimer) {
      clearTimeout(cooldownTimer);
      cooldownTimer = null;
    }

    broadcastModeChange('RAPID');
  }

  function scheduleNormalReturn() {
    if (cooldownTimer) clearTimeout(cooldownTimer);
    cooldownTimer = setTimeout(() => {
      enterNormalMode();
      cooldownTimer = null;
    }, RAPID_COOLDOWN_MS);
  }

  /**
   * Core sample-and-detect loop.
   * Called at the current mode's interval.
   */
  function sampleAndDetect() {
    if (!grabFrameFn || !roiCoordsFn) return;
    
    const roi = roiCoordsFn();
    if (!roi) return;
    
    const frame = grabFrameFn(roi);
    if (!frame || frame.error) return;

    stats.framesSampled++;

    // Detect feed icon using the frame's raw pixel data
    let feedPresent = false;
    
    if (frame.imageData) {
      feedPresent = FeedDetector.detect(frame.imageData);
    }

    if (feedPresent) {
      stats.framesWithIcon++;
      lastIconDetectedTime = Date.now();
    }

    // Broadcast frame preview to side panel
    chrome.runtime.sendMessage({
      action: "frame-previews",
      raw: frame.dataUrl,
      status: feedPresent ? "icon-detected" : "monitoring",
      diagnostics: {
        mode: mode,
        pixelDiff: frame.meanDiff || 0,
        feedDetector: FeedDetector.getDiagnostics(),
        scheduler: TransmissionScheduler.getDiagnostics(),
        engine: getDiagnostics()
      }
    }).catch(() => {});

    // Decision engine
    if (feedPresent && mode === 'NORMAL') {
      enterRapidMode();
    }
    
    if (mode === 'RAPID') {
      if (feedPresent) {
        // Feed still active — evaluate for transmission
        TransmissionScheduler.evaluate(frame);
        // Reset cooldown timer
        if (cooldownTimer) {
          clearTimeout(cooldownTimer);
          cooldownTimer = null;
        }
      } else {
        // Feed gone — start cooldown to return to normal
        if (!cooldownTimer) {
          scheduleNormalReturn();
        }
      }
    }
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
      normalModeTime: Math.round(stats.normalModeTime / 1000),
      rapidModeTime: Math.round(stats.rapidModeTime / 1000),
      modeTransitions: stats.modeTransitions,
      sessionDurationSec: Math.round(sessionDuration),
      currentIntervalMs: mode === 'RAPID' ? RAPID_INTERVAL_MS : NORMAL_INTERVAL_MS,
      cooldownActive: !!cooldownTimer,
      timeSinceLastIcon: lastIconDetectedTime ? Math.round((now - lastIconDetectedTime) / 1000) : null
    };
  }

  return { init, start, stop, getDiagnostics };
})();
