"""
FragEngine V0.16 — Desktop Screen Capture Module
High-performance screen capture powered by mss for DirectX / Fullscreen game ingest.
"""

import time
import cv2
import numpy as np
import mss

class DesktopCapturer:
    def __init__(self):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors

    def get_monitors(self):
        """Returns list of available monitors."""
        return self.monitors

    def capture_roi(self, roi_coords, monitor_idx=1):
        """
        Captures a specific ROI bounding box from target monitor.
        :param roi_coords: dict with keys {'top', 'left', 'width', 'height'}
        :param monitor_idx: monitor index (default 1 for primary display)
        :return: OpenCV BGR numpy array image, or None
        """
        try:
            if not roi_coords:
                return None

            # Get target monitor offset
            mon = self.monitors[monitor_idx] if monitor_idx < len(self.monitors) else self.monitors[1]
            
            bbox = {
                "top": int(mon["top"] + roi_coords["top"]),
                "left": int(mon["left"] + roi_coords["left"]),
                "width": int(roi_coords["width"]),
                "height": int(roi_coords["height"])
            }

            sct_img = self.sct.grab(bbox)
            # Convert mss BGRA image to BGR numpy array
            img = np.array(sct_img, dtype=np.uint8)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img_bgr
        except Exception as e:
            print(f"[DesktopCapturer Error] {e}")
            return None

    def capture_full_screen(self, monitor_idx=1):
        """Captures full monitor screenshot for interactive ROI calibration."""
        mon = self.monitors[monitor_idx] if monitor_idx < len(self.monitors) else self.monitors[1]
        sct_img = self.sct.grab(mon)
        img = np.array(sct_img, dtype=np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
