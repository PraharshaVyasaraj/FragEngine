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
  const NORMAL_INTERVAL_MS = 500; // Sample every 500ms (V0.16)
  const RAPID_INTERVAL_MS = 200;  // Sample every 200ms
  const RAPID_LOCK_DURATION_MS = 1500; // Stay in Rapid mode for 1.5s lock (V0.14.2)

  let mode = 'IDLE';  // 'IDLE', 'NORMAL', 'RAPID'
  let intervalId = null;
  let rapidModeLockedUntil = 0; // Expiration timestamp for fight window lock
  let lastIconDetectedTime = 0;
  let lastPreviewTime = 0; // Throttle preview ticks (V0.14.2)
  let lastActivityTime = 0; // Timestamp of last visual/detection activity

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
    lastActivityTime = Date.now();
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
    mode = 'IDLE';
    rapidModeLockedUntil = 0;
  }

  function enterNormalMode() {
    // Accumulate rapid time if switching from rapid
    if (mode === 'RAPID' && modeStartTime) {
      stats.rapidModeTime += Date.now() - modeStartTime;
    }
    
    mode = 'NORMAL';
    modeStartTime = Date.now();
    rapidModeLockedUntil = 0;
    lastActivityTime = Date.now();
    
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(sampleAndDetect, NORMAL_INTERVAL_MS);

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
    rapidModeLockedUntil = Date.now() + RAPID_LOCK_DURATION_MS; // Lock Fight Window (1.5s)
    
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(sampleAndDetect, RAPID_INTERVAL_MS);

    broadcastModeChange('RAPID');
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
      
      // Extend Fight Window lock if we detect a new icon during Rapid mode
      if (mode === 'RAPID') {
        rapidModeLockedUntil = Date.now() + RAPID_LOCK_DURATION_MS;
      }
    }

    const now = Date.now();

    if (feedPresent || frame.hasChanged) {
      lastActivityTime = now;
    }

    const shouldSendPreview = feedPresent || (now - lastPreviewTime >= 1000);
    if (shouldSendPreview) {
      lastPreviewTime = now;
    }

    // Broadcast frame preview to side panel
    chrome.runtime.sendMessage({
      action: "frame-previews",
      raw: shouldSendPreview ? frame.dataUrl : null,
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
    if (mode === 'NORMAL') {
      if (feedPresent) {
        enterRapidMode();
      }
    } else if (mode === 'RAPID') {
      if (feedPresent) {
        // Feed active — evaluate for transmission
        TransmissionScheduler.evaluate(frame);
      } else {
        // Feed silent — check if Fight Window has expired
        if (now >= rapidModeLockedUntil) {
          enterNormalMode();
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
    const isLocked = mode === 'RAPID' && now < rapidModeLockedUntil;
    
    return {
      mode,
      framesSampled: stats.framesSampled,
      framesWithIcon: stats.framesWithIcon,
      normalModeTime: Math.round(stats.normalModeTime / 1000),
      rapidModeTime: Math.round(stats.rapidModeTime / 1000),
      modeTransitions: stats.modeTransitions,
      sessionDurationSec: Math.round(sessionDuration),
      currentIntervalMs: mode === 'RAPID' ? RAPID_INTERVAL_MS : NORMAL_INTERVAL_MS,
      cooldownActive: isLocked,
      timeSinceLastIcon: lastIconDetectedTime ? Math.round((now - lastIconDetectedTime) / 1000) : null
    };
  }

  return { init, start, stop, getDiagnostics };
})();
