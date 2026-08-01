/**
 * FragEngine V0.16 — Sampling Engine
 * Fixed Standard 250ms Ingest Engine.
 */

const SamplingEngine = (() => {
  const SAMPLING_INTERVAL_MS = 250; // Fixed 250ms sampling rate

  let mode = 'IDLE'; // 'IDLE', 'RUNNING'
  let intervalId = null;

  // Session stats
  let sessionStartTime = null;
  let stats = {
    framesSampled: 0,
    framesWithIcon: 0
  };

  let grabFrameFn = null;
  let roiCoordsFn = null;

  function init(grabFrame, getRoi) {
    grabFrameFn = grabFrame;
    roiCoordsFn = getRoi;
  }

  function start() {
    if (mode === 'RUNNING') return;
    sessionStartTime = Date.now();
    stats = {
      framesSampled: 0,
      framesWithIcon: 0
    };
    TransmissionScheduler.reset();
    mode = 'RUNNING';
    
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(sampleAndDetect, SAMPLING_INTERVAL_MS);

    broadcastModeChange('RUNNING');
  }

  function stop() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    mode = 'IDLE';
    broadcastModeChange('IDLE');
  }

  function sampleAndDetect() {
    if (!grabFrameFn || !roiCoordsFn) return;
    
    const roi = roiCoordsFn();
    if (!roi) return;
    
    const frame = grabFrameFn(roi);
    if (!frame || frame.error) return;

    stats.framesSampled++;

    let feedPresent = false;
    if (frame.imageData) {
      feedPresent = FeedDetector.detect(frame.imageData);
    }

    if (feedPresent) {
      stats.framesWithIcon++;
    }

    // Always enqueue frame to transmission scheduler at 250ms rate
    TransmissionScheduler.enqueue(frame);

    // Broadcast frame preview to side panel / popup
    chrome.runtime.sendMessage({
      action: "frame-previews",
      raw: frame.dataUrl,
      status: feedPresent ? "icon-detected" : "ingesting",
      diagnostics: {
        mode: "STANDARD_250MS",
        pixelDiff: frame.meanDiff || 0,
        feedDetector: FeedDetector.getDiagnostics(),
        scheduler: TransmissionScheduler.getDiagnostics(),
        engine: getDiagnostics()
      }
    }).catch(() => {});
  }

  function broadcastModeChange(newMode) {
    chrome.runtime.sendMessage({
      action: "sampling-mode-changed",
      mode: newMode,
      intervalMs: SAMPLING_INTERVAL_MS
    }).catch(() => {});
  }

  function getDiagnostics() {
    return {
      mode: mode,
      intervalMs: SAMPLING_INTERVAL_MS,
      framesSampled: stats.framesSampled,
      framesWithIcon: stats.framesWithIcon,
    };
  }

  return { init, start, stop, getDiagnostics };
})();
