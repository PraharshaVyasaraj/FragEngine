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
  // Tunable thresholds
  const SATURATION_THRESHOLD = 0.25;  // Min saturation to count as "colored" (V0.14.1)
  const BRIGHTNESS_MIN = 80;          // Min brightness (ignore dark noise)
  const ICON_PIXEL_RATIO = 0.005;     // 0.5% of ROI pixels must be colored (V0.14.1)

  // Diagnostics (exposed for popup)
  let lastResult = {
    feedPresent: false,
    saturationScore: 0,
    coloredPixels: 0,
    totalPixels: 0,
    avgBrightness: 0,
    detectedRegion: null // 'left', 'center', 'right' — where the color cluster is
  };

  /**
   * Detect if a kill feed icon is present in the given ImageData.
   * @param {ImageData} imageData — from canvas.getImageData()
   * @returns {boolean} true if feed icon is likely present
   */
  function detect(imageData) {
    const pixels = imageData.data;
    const totalPixels = pixels.length / 4;
    
    let coloredPixelCount = 0;
    let brightnessSum = 0;
    
    // Track colored pixel positions for region detection
    let coloredLeftCount = 0;
    let coloredCenterCount = 0;
    let coloredRightCount = 0;
    const width = imageData.width;
    const thirdWidth = Math.floor(width / 3);

    for (let i = 0; i < pixels.length; i += 4) {
      const r = pixels[i];
      const g = pixels[i + 1];
      const b = pixels[i + 2];
      
      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      const saturation = max === 0 ? 0 : (max - min) / max;
      
      brightnessSum += max;

      if (saturation > SATURATION_THRESHOLD && max > BRIGHTNESS_MIN) {
        coloredPixelCount++;
        
        // Determine which third of the image this pixel is in
        const pixelIndex = i / 4;
        const x = pixelIndex % width;
        if (x < thirdWidth) {
          coloredLeftCount++;
        } else if (x < thirdWidth * 2) {
          coloredCenterCount++;
        } else {
          coloredRightCount++;
        }
      }
    }

    const ratio = coloredPixelCount / totalPixels;
    const avgBrightness = brightnessSum / totalPixels;
    
    // Determine which region has the most colored pixels
    let detectedRegion = null;
    if (coloredPixelCount > 0) {
      const maxRegion = Math.max(coloredLeftCount, coloredCenterCount, coloredRightCount);
      if (maxRegion === coloredLeftCount) detectedRegion = 'left';
      else if (maxRegion === coloredCenterCount) detectedRegion = 'center';
      else detectedRegion = 'right';
    }

    const feedPresent = ratio >= ICON_PIXEL_RATIO;

    // Store diagnostics
    lastResult = {
      feedPresent,
      saturationScore: Math.round(ratio * 10000) / 10000,
      coloredPixels: coloredPixelCount,
      totalPixels,
      avgBrightness: Math.round(avgBrightness),
      detectedRegion
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
