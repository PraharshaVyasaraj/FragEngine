/**
 * FragEngine V0.14 — Feed Detector
 * Color saturation heuristic for kill feed icon detection.
 * 
 * Kill feed icons (KNOCK, FINISH, DROWN, FALL, ZONE) are the only
 * high-saturation colored elements in the ROI. Player names are 
 * white/gray text on dark semi-transparent background.
 * 
 * This module answers ONE question: "Is a kill feed icon visible?"
 */

const FeedDetector = (() => {
  // Tunable thresholds (V0.14.2)
  const BINARIZATION_THRESHOLD = 180; // Brightness cutoff for binarization (0-255)
  const DENSITY_MIN = 0.03;           // 3% min density of white pixels
  const DENSITY_MAX = 0.30;           // 30% max density of white pixels

  // Diagnostics (exposed for popup)
  let lastResult = {
    feedPresent: false,
    saturationScore: 0, // Used for binarization ratio in popup.js compatibility
    whitePixels: 0,
    totalPixels: 0,
    avgBrightness: 0
  };

  /**
   * Detect if a kill feed icon is present in the given ImageData.
   * @param {ImageData} imageData — from canvas.getImageData()
   * @returns {boolean} true if feed icon is likely present
   */
  function detect(imageData) {
    const pixels = imageData.data;
    const totalPixels = pixels.length / 4;
    
    let whitePixelCount = 0;
    let brightnessSum = 0;
    
    for (let i = 0; i < pixels.length; i += 4) {
      const r = pixels[i];
      const g = pixels[i + 1];
      const b = pixels[i + 2];
      
      // Standard Luma conversion
      const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
      brightnessSum += brightness;

      // Threshold at 180 to count active white pixels (names and icons)
      if (brightness >= BINARIZATION_THRESHOLD) {
        whitePixelCount++;
      }
    }

    const ratio = whitePixelCount / totalPixels;
    const avgBrightness = brightnessSum / totalPixels;
    
    // Gating logic: active kill feed sits in 3% to 30% white pixel density range
    const feedPresent = ratio >= DENSITY_MIN && ratio <= DENSITY_MAX;

    // Store diagnostics
    lastResult = {
      feedPresent,
      saturationScore: Math.round(ratio * 10000) / 10000, // Kept key name for popup compatibility
      whitePixels: whitePixelCount,
      totalPixels,
      avgBrightness: Math.round(avgBrightness)
    };

    return feedPresent;
  }

  /**
   * Get the last detection result for diagnostics.
   * @returns {Object} diagnostic data from the last detect() call
   */
  function getDiagnostics() {
    return { ...lastResult };
  }

  return { detect, getDiagnostics };
})();
