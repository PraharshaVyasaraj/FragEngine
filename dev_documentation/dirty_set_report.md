# V1 Telemetry Report: Dirty Set Analysis & Hypothetical Log Sequence

This report evaluates the extraction accuracy of the Feed Parser V1 on the `Dirty set` (7 images with high compression, low resolution, or environmental noise) and presents a simulated match telemetry log stream.

---

## 📊 Part 1: Image-by-Image Extraction Report

Here is the exact analysis of what the binarization, EasyOCR, and template-matching pipeline extracted from each screenshot (including 3x upscaled configurations):

### 1. `Screenshot 2026-05-25 172459.png`
*   **Resolution:** `160x20` (Ultra-low Resolution)
*   **Layout:** `UNKNOWN`
*   **T1 (Attacker):** `None` (Failed to read)
*   **I2 (State):** `None` (Failed to match)
*   **T2 (Victim):** `None`
*   **Wall Status:** 🛑 **BLOCKED**
*   *Diagnostic:* The image is too small (20px high) for the OCR system to locate text lines, even with upscaling.

### 2. `Screenshot 2026-05-25 172509.png`
*   **Resolution:** `479x62` (Standard HUD Resolution)
*   **Layout:** `2T2I` (Player vs. Player)
*   **T1 (Attacker):** `OG_Gongoop`
*   **I2 (State):** `FINISH` (Match Score: `0.7941`)
*   **T2 (Victim):** `NRL~Tryzod`
*   **Wall Status:** 🟢 **PASSED**

### 3. `Screenshot 2026-05-25 174711.png`
*   **Resolution:** `324x36` (Standard HUD Resolution)
*   **Layout:** `2T2I` (Player vs. Player)
*   **T1 (Attacker):** `RUINS-SHOCKx`
*   **I2 (State):** `FINISH` (Match Score: `0.7941`)
*   **T2 (Victim):** `StorkanZo`
*   **Wall Status:** 🟢 **PASSED**

### 4. `Screenshot 2026-05-25 174715.png`
*   **Resolution:** `349x43` (Standard HUD Resolution)
*   **Layout:** `2T2I` (Player vs. Player)
*   **T1 (Attacker):** `SRV~HowkPloyzzz`
*   **I2 (State):** `FINISH` (Match Score: `0.7941`)
*   **T2 (Victim):** `StorTYROXw`
*   **Wall Status:** 🟢 **PASSED**

### 5. `Screenshot 2026-05-25 174811.png`
*   **Resolution:** `166x21` (Ultra-low Resolution)
*   **Layout:** `1T2I` (Read as Environmental due to partial OCR miss)
*   **T1 (Victim):** `FETHRASPIEII` (Original text: `FETHRxSPLEIL`)
*   **I1 (Cause):** `UNKNOWN` (Score: `0.00` - shape distorted by upscale blurring)
*   **I2 (State):** `UNKNOWN` (Score: `0.00`)
*   **T2 (Victim 2):** `None`
*   **Wall Status:** 🛑 **BLOCKED** (Match scores below threshold)

### 6. `Screenshot 2026-05-25 174819.png`
*   **Resolution:** `181x17` (Ultra-low Resolution)
*   **Layout:** `1T2I` (Read as Environmental due to partial OCR miss)
*   **T1 (Victim):** `FETHPXSAMURXI`
*   **I1 (Cause):** `DROWN` (Match Score: `0.15` - matching on blur)
*   **I2 (State):** `FINISH` (Match Score: `0.10` - matching on blur)
*   **T2 (Victim 2):** `None`
*   **Wall Status:** 🛑 **BLOCKED** (Match scores below threshold)

### 7. `Screenshot 2026-05-25 174847.png`
*   **Resolution:** `501x51` (Standard HUD Resolution)
*   **Layout:** `1T2I` (Environmental)
*   **T1 (Victim):** `Tr CHAMP-OB`
*   **I1 (Cause):** `ZONE` (Match Score: `0.6033` against playzone template)
*   **I2 (State):** `FINISH` (Match Score: `0.7941`)
*   **T2 (Victim 2):** `None`
*   **Wall Status:** 🟢 **PASSED**

---

## 📈 Part 2: Hypothetical Chronological Match Log

Assuming these events took place sequentially during a match, "The Wall" gatekeeper filters the raw frame inputs (captured at 5 FPS) and writes the following **chronological log stream** to `QL.csv`:

```text
Log # | Layout Type | T1             | I1     | I2     | T2
Log 1 | 2T2I        | OG_Gongoop     | Weapon | FINISH | NRL~Tryzod
Log 2 | 2T2I        | RUINS-SHOCKx   | Weapon | FINISH | StorkanZo
Log 3 | 2T2I        | SRV~HowkPloyzzz| Weapon | FINISH | StorTYROXw
Log 4 | 1T2I        | Tr CHAMP-OB    | ZONE   | FINISH | None
```

### 🧠 Gatekeeper Flow Simulation (Timeline):

1.  **Time 00:02.0:** Raw frame reads `OG_Gongoop FINISH NRL~Tryzod` ➔ **The Wall: APPROVED** ➔ Written as **Log 1**.
2.  **Time 00:02.2 to 00:03.4:** Raw frames read duplicate `OG_Gongoop FINISH NRL~Tryzod` ➔ **The Wall: BLOCKED** (Duplicate detected, discarded).
3.  **Time 00:05.0:** Raw frame reads `RUINS-SHOCKx FINISH StorkanZo` ➔ **The Wall: APPROVED** ➔ Written as **Log 2**.
4.  **Time 00:09.2:** Raw frame reads `SRV~HowkPloyzzz FINISH StorTYROXw` ➔ **The Wall: APPROVED** ➔ Written as **Log 3**.
5.  **Time 00:10.0 to 00:10.4:** Raw frame reads a blurry transition ➔ **The Wall: BLOCKED** (Missing OCR text/low confidence, discarded).
6.  **Time 00:12.6:** Raw frame reads `Tr CHAMP-OB ZONE FINISH` ➔ **The Wall: APPROVED** ➔ Written as **Log 4**.
7.  **Time 00:15.0:** User camera downscales to skybox causing low-res (20px high) feed on `FETHRASPIEII` ➔ **The Wall: BLOCKED** (OCR failure/low template match score, discarded).
