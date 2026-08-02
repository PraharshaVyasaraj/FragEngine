# FragEngine V0.13 — SESSION_0006 Quality Log Deep Analysis

> **Session**: SESSION_0006 | **QL Entries Analysed**: 230 | **Baseline**: V0.13 CPU (EasyOCR PyTorch)

---

## 1. What the QL Data Proves Works ✅

### Team Tag Recognition
The engine correctly identifies structured team tags consistently:
- `NxTISWAG`, `NH-TOJI`, `NH-JEENESH`, `HYDRA-URDOWNFAL`, `HYDRA-FURY`, `HYDRA-FLASH`
- `LIXR-EGO`, `XBUG-SHINZO`, `XBUG-VOID`, `XBUG-REBORN`
- `PLTN-ARYONOP`, `PLTN-FRAGY`, `PLTN-EVILKIDZ`, `PLTM-RULER`
- `TRX-R4JPUT`, `CPTNxBALDEV`, `CPTNxZUXXY`
- `VEERxMONARCH`, `VEERxAGNIX4G`, `STORXENO`, `STORKOYLZ`

**Evidence**: Tags with clear separator characters (`-`, `x`, `~`, `*`) are correctly parsed into `T1`/`T2` layout columns, proving the separator logic from V0.11/V0.12 is working.

### Icon Classification
- `KNOCK`, `FINISH`, `DROWN`, `FALL`, `ZONE` all fire correctly
- 2T2I and 1T2I layout detection is consistently accurate
- `WEAPON` sub-type is reliably identified as the delivery mechanism

### Deduplication Gate (Working but undertriggered)
- Row 54–57: `HYDRA-FURY KNOCK/FINISH VEERxMONOR` — same kill captured 4 times
- Rows 7–8, 160–164, 195–198: Repeated events passing through

**Proof**: The 409 suppressed duplicates in the telemetry confirm the gate IS working — these are the ones that **escaped** the gate, which is a ~2.5 second OCR latency problem, not a logic problem.

---

## 2. OCR Error Taxonomy (Categorised from QL Evidence)

### Category A — Character Substitution (Most Common)
OCR confuses visually similar characters at small font sizes:

| Correct | OCR Output | Examples from QL |
|---------|-----------|-----------------|
| `H` | `M` | `PLTM-` instead of `PLTN-` (rows 128, 132, 134) |
| `O` | `0` / `C` | `HVORA` instead of `HYDRA` (rows 52, 168) |
| `N` | `M` / `H` | `MH-JEENESH` instead of `NH-JEENESH` (row 182) |
| `D` | `L` | `REBDRN` instead of `REBORN` (rows 96, 101, 103, 106) |
| `G` | `C` / `6` | `STORCODx` instead of `STORGODx` (row 176) |
| `U` | `V` | `WEONTS` instead of `WEUNTS` (rows 138, 139) |
| `Y` | `V` | `STORCLOVDIY` instead of `STORCLOUDIY` (row 154) |

**Root Cause**: EasyOCR's CRNN recognizer at 2–3ms/pixel resolution struggles with the game's high-contrast bold font at 24px height. These are single-pixel ambiguities that OpenVINO GPU inference won't fix alone — needs **morphological upscaling** before inference (4x INTER_CUBIC).

### Category B — Name Truncation (Critical)
Many entries are cut at the right edge of the ROI:

| Truncated | Expected |
|-----------|----------|
| `HYDRA-` (row 24) | `HYDRA-URDOWNFAL` |
| `VEE` (row 50) | `VEERU` |
| `CPT` (row 73) | `CPTNxZUXXY` |
| `PLTN-` (rows 69, 122, 144) | `PLTN-ARYONOP` |
| `STORCL` (row 155) | `STORCLOUDIY` |
| `LR-EGO` (row 39) | `LIXR-EGO` |

**Root Cause**: The ROI crop box is **not wide enough** to capture full names. This is a calibration width issue. The crop is cutting off 3–6 characters on the right edge. **V0.13.3 fix** (auto-lock) will help consistency, but the user needs to widen the ROI during calibration.

### Category C — Special Character Injection
OCR hallucinates punctuation into the kill feed text:

| Injected Character | Examples |
|-------------------|----------|
| `}` | `VEERxAGNI}` (row 46), `CPTHx}` (row 185) |
| `[` | `ARCNXX[` (row 38) |
| `)` | `LIXR-)` (row 119) |
| `:` | `ARCNX:` (row 98) |
| `_` | `STORXEN_` (row 163) |

**Root Cause**: The game UI renders small decorative glyphs (borders, score separators) near the kill feed text. EasyOCR's text detector bleeds into those adjacent pixels and merges them into the word boundary.

### Category D — Prefix Stripping / Partial Left Edge Loss
| OCR Output | Full Name | Issue |
|-----------|-----------|-------|
| `REBDRN` | `XBUG-REBORN` | `XBUG-` prefix lost |
| `IKOOY` | `NxTIKOKOOY` | `NxT` prefix lost |
| `VOID` | `XBUG-VOID` | `XBUG-` prefix lost |
| `SHINZO` | `XBUG-SHINZO` | `XBUG-` prefix lost |
| `FRAGY` | `PLTN-FRAGY` | `PLTN-` prefix lost |

**Root Cause**: Left edge of the ROI is starting slightly inside the kill feed text boundary. The team prefix gets cut off on the left side. This is a calibration x-offset issue (ROI starts too far right).

---

## 3. Deduplication Effectiveness

From 230 QL entries, grouping by actual kill events:

| Kill Group | Unique Event | Duplicate Entries | Ratio |
|-----------|-------------|-------------------|-------|
| HYDRA-FURY → VEERxMONOR | 1 kill | Rows 54, 55, 56, 57 (4 entries) | 4:1 |
| XBUG-REBORN → ARCNXxLAKSH | 1 kill | Rows 97–106 (10 entries) | 10:1 |
| PLTN-ARYONOP → NH-JEENESH | 1 kill | Rows 182, 183, 188–192 (7 entries) | 7:1 |
| CPTNxBALDEV → CPTNxBALDEV | 1 kill | Rows 225–230 (6 entries) | 6:1 |

**Verdict**: The gate catches most but at 2.5s OCR latency, the same kill fires 4–10 requests before the cooldown timer blocks them. **V0.14 target**: Drop OCR to <100ms so the cooldown timer can block duplicates before the next frame even arrives.

---

## 4. UNKNOWN Icon Misses — Root Cause

1T2I events with `UNKNOWN UNKNOWN` (rows 5, 9, 10, 11, 32, 64, 70, etc.) mean the icon template matcher found no match.

**Why**: These frames likely contain:
- A death icon type not in your `SF FEED ICONS` template library
- Motion blur during the OCR window (frame arrived mid-transition)
- Low-confidence OCR on the icon area due to 2.5s delay (frame already gone by the time we process)

---

## 5. Bugs to Fix Based on QL Evidence

| Bug | Priority | Fix |
|-----|----------|-----|
| ROI too narrow (right truncation) | 🔴 High | Widen default ROI from 240px to 320px |
| ROI x-offset too far right (left prefix loss) | 🔴 High | Shift ROI start point 10–15px left |
| Special char injection `}`, `[`, `)` | 🟡 Medium | Post-process: strip non-alphanumeric except `-`, `x`, `~`, `*`, `_` |
| CSV Export never worked (V0.1–V0.13.2) | ✅ Fixed | V0.13.3: Blob + `chrome.downloads.download()` |
| Duplicate suppression weak at 2.5s latency | 🔵 V0.14 | OpenVINO iGPU → <100ms OCR |

---

## 6. V0.13.3 Patch Summary (Applied Today)

| # | Change |
|---|--------|
| **13.3-A** | **CSV Export Fixed**: `encodeURI` + `data:` URI replaced with `Blob` + `URL.createObjectURL` + `chrome.downloads.download()`. Fields now quoted to handle commas in player names. Auto-timestamped filenames (`FragEngine_QL_YYYYMMDD_HHMM.csv`). |
| **13.3-B** | **`downloads` permission** added to `manifest.json` (was the root blocker from V0.1 onward). |

---

## 7. V0.14 Targets — Confirmed by This Evidence

| Metric | V0.13 Baseline | V0.14 OpenVINO Target | Evidence |
|--------|---------------|-----------------------|---------|
| OCR latency avg | 2,456 ms | < 100 ms | 4–10 duplicate entries per kill event |
| CPU peak | 100% | < 20% | Hardware telemetry CSV |
| Char substitution errors | ~15% of entries | < 3% | Category A errors above |
| Right truncation (ROI width) | ~8% of entries | 0% | Category B errors above |
| Special char injection | ~5% of entries | ~1% | Category C errors above |
