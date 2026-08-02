# V1 Telemetry Extraction & Bounding Box Analysis

This document contains the detailed diagnostic report, OCR extractions, template matching scores, and gatekeeper decisions for the 7 screenshots in the **Dirty set**.

## 🖼️ File: `Screenshot 2026-05-25 172459.png`

* **Original Resolution:** `160x20`
* **OCR Bounding Box Count:** `0` found

> [!WARNING]
> **The Wall Status: BLOCKED** (No text components found). The crop is too low-resolution for the OCR network.

---

## 🖼️ File: `Screenshot 2026-05-25 172509.png`

* **Original Resolution:** `479x62`
* **OCR Bounding Box Count:** `2` found
* **Classified Layout:** `2T2I`
* **T1 (Attacker/Victim Name):** `OG_Gongoop`
* **T2 (Victim Name):** `NRL~Tryzod`

### 🏷️ Icon Match Details
* **Icon 1 (Weapon):** Hardcoded to `Weapon` for V1
* **Icon 2 (State):** Matched as `FINISH` (Score: `0.7885`)
  * *Details:* `KNOCK`: `0.1051`, `FINISH`: `0.7885`

> [!NOTE]
> **The Wall Status: PASSED**
> **QL Telemetry Entry:** `Log # | 2T2I | OG_Gongoop | Weapon | FINISH | NRL~Tryzod`

---

## 🖼️ File: `Screenshot 2026-05-25 174711.png`

* **Original Resolution:** `324x36`
* **OCR Bounding Box Count:** `2` found
* **Classified Layout:** `2T2I`
* **T1 (Attacker/Victim Name):** `RUINS-SHOCKx`
* **T2 (Victim Name):** `StorkanZo`

### 🏷️ Icon Match Details
* **Icon 1 (Weapon):** Hardcoded to `Weapon` for V1
* **Icon 2 (State):** Matched as `FINISH` (Score: `0.7888`)
  * *Details:* `KNOCK`: `0.0790`, `FINISH`: `0.7888`

> [!NOTE]
> **The Wall Status: PASSED**
> **QL Telemetry Entry:** `Log # | 2T2I | RUINS-SHOCKx | Weapon | FINISH | StorkanZo`

---

## 🖼️ File: `Screenshot 2026-05-25 174715.png`

* **Original Resolution:** `349x43`
* **OCR Bounding Box Count:** `2` found
* **Classified Layout:** `2T2I`
* **T1 (Attacker/Victim Name):** `SRV~HowkPloyzzz`
* **T2 (Victim Name):** `StorTYROXw`

### 🏷️ Icon Match Details
* **Icon 1 (Weapon):** Hardcoded to `Weapon` for V1
* **Icon 2 (State):** Matched as `FINISH` (Score: `0.7861`)
  * *Details:* `KNOCK`: `0.0868`, `FINISH`: `0.7861`

> [!NOTE]
> **The Wall Status: PASSED**
> **QL Telemetry Entry:** `Log # | 2T2I | SRV~HowkPloyzzz | Weapon | FINISH | StorTYROXw`

---

## 🖼️ File: `Screenshot 2026-05-25 174811.png`

* **Original Resolution:** `166x21`
* **OCR Bounding Box Count:** `1` found
* **Classified Layout:** `1T2I`
* **T1 (Attacker/Victim Name):** `FETHRASPIEII`
* **T2 (Victim Name):** `None`

### 🏷️ Icon Match Details
* **Icon 1 (Hazard):** Matched as `UNKNOWN` (Score: `-1.0000`)
* **Icon 2 (State):** Matched as `UNKNOWN` (Score: `-1.0000`)

> [!WARNING]
> **The Wall Status: BLOCKED** (Reason: Icon 2 Match score (-1.00) below 0.65 threshold)

---

## 🖼️ File: `Screenshot 2026-05-25 174819.png`

* **Original Resolution:** `181x17`
* **OCR Bounding Box Count:** `1` found
* **Classified Layout:** `1T2I`
* **T1 (Attacker/Victim Name):** `FETHPXSAMURXI`
* **T2 (Victim Name):** `None`

### 🏷️ Icon Match Details
* **Icon 1 (Hazard):** Matched as `DROWN` (Score: `0.1532`)
  * *Details:* `ZONE`: `0.1179`, `FALL`: `-0.0668`, `DROWN`: `0.1532`
* **Icon 2 (State):** Matched as `FINISH` (Score: `0.1035`)
  * *Details:* `KNOCK`: `0.0489`, `FINISH`: `0.1035`

> [!WARNING]
> **The Wall Status: BLOCKED** (Reason: Icon 2 Match score (0.10) below 0.65 threshold)

---

## 🖼️ File: `Screenshot 2026-05-25 174847.png`

* **Original Resolution:** `501x51`
* **OCR Bounding Box Count:** `1` found
* **Classified Layout:** `1T2I`
* **T1 (Attacker/Victim Name):** `Tr CHAMP-OB`
* **T2 (Victim Name):** `None`

### 🏷️ Icon Match Details
* **Icon 1 (Hazard):** Matched as `ZONE` (Score: `0.5969`)
  * *Details:* `ZONE`: `0.5969`, `FALL`: `-0.1005`, `DROWN`: `0.1609`
* **Icon 2 (State):** Matched as `FINISH` (Score: `0.7923`)
  * *Details:* `KNOCK`: `0.0714`, `FINISH`: `0.7923`

> [!NOTE]
> **The Wall Status: PASSED**
> **QL Telemetry Entry:** `Log # | 1T2I | Tr CHAMP-OB | ZONE | FINISH | None`

---
