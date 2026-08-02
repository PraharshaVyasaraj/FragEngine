# Desktop Spectator Engine — Complexities, Edge Cases & Safeguards

This document details technical complexities and architectural safeguards when running **FragEngine Desktop Spectator Client (`spectator_client.py`)** alongside a live game client (e.g. Scarfall at 250% UI scale).

---

## ⚠️ Technical Complexities & Solutions

### 1. Multi-Monitor Coordinate Resolution
* **Complexity**: In multi-monitor broadcast setups (Monitor 1: Game Client 1080p, Monitor 2: Control Dashboard 4K), standard relative canvas coordinates fail due to display DPI scaling and OS monitor offsets.
* **Safeguard**: `DesktopCapturer` leverages `mss.monitors[target_idx]` to compute absolute virtual screen coordinates `(mon["left"] + roi["left"])`, maintaining 100% pixel locking across display setups.

---

### 2. Fullscreen Exclusive vs. Borderless Windowed Focus Loss
* **Complexity**: Direct 3D games running in "Exclusive Fullscreen" suspend DirectX frame buffer updates when alt-tabbing or shifting cursor focus to the Control Center app window.
* **Safeguard**: 
  1. **Recommended Observer Practice**: Game display mode set to **Borderless Windowed** (standard for esports production).
  2. **DirectX Desktop Duplication**: `mss` grabs hardware Desktop Duplication surfaces directly from the GPU compositor, capturing frames even when the game window is inactive.

---

### 3. Resolution & DPI Scale Auto-Snapping
* **Complexity**: Changing graphics settings or DPI scale (e.g. 100% to 125% Windows DPI) shifts pixel ROI boundaries.
* **Safeguard**: ROI calibration boundaries are stored internally as proportional percentages (`left_pct`, `top_pct`, `width_pct`, `height_pct`). When display resolution changes, pixel bounding boxes auto-rescale dynamically.

---

### 4. In-Game Menu & Map Overlay Noise Suppression
* **Complexity**: When a spectator opens the full-screen map (`M`), pause menu (`ESC`), or scoreboard overlay (`TAB`), the crop area captures non-feed menu UI.
* **Safeguard**:
  * **Background Brightness Wall**: `server.py` checks mean grayscale brightness. If `mean_brightness > 90` (map/menu UI noise), OCR is bypassed instantly (<0.1ms).
  * **Ground-Truth Sanity Check**: `StateEngine` cross-references `Teams Alive` ROI counter before finalizing team wipe rank assignments.
