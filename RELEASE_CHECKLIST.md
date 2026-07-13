# FragEngine Maintenance & Release Operations Guide

This document outlines the directory structure and the mandatory checklist that must be executed during every major and minor update of the FragEngine repository.

---

## 1. Directory Structure Map

```
FragEngine/
├── chrome_extension/               # Client-Side Extension Module (V0.14+)
│   ├── manifest.json               # Extension configuration & permission gates
│   ├── background.js               # Service worker (manages lifecycle & sidepanel)
│   ├── content.js                  # Injects canvas frames and interacts with video
│   ├── feed_detector.js            # Binarization density checks (white pixels 3-30%)
│   ├── sampling_engine.js          # State machine loop (NORMAL/RAPID/IDLE states)
│   ├── transmission_scheduler.js   # POST transmission throttling (800ms limit)
│   ├── popup.html                  # Diagnostic dashboard interface
│   ├── popup.js                    # UI update controller & local binarization preview
│   └── popup.css                   # Custom glassmorphism UI styles
│
├── backend/                        # Telemetry, WMI Sampling & Helper Utilities
│   ├── __init__.py                 # Packages backend module
│   └── telemetry.py                # TelemetryCollector: hardware & latency logs
│
├── data/                           # Ingested Game Session Outputs
│   └── sessions/                   # Unique capture directories (SESSION_XXXX/)
│       ├── QL.csv                  # Parsed events log (layout, players, icons)
│       ├── v0.14_telemetry.csv     # Telemetry log (CPU, GPU, RAM, latencies)
│       └── v0.14_summary.json      # Aggregated performance metadata
│
├── version_history/                # Changelogs and Version Timelines
│   ├── v0.11_history.md
│   ├── v0.12_history.md
│   ├── v0.13_history.md
│   └── v0.14_history.md
│
├── tests/                          # Automated Regression Test Suites
│   ├── test_easyocr.py             # OCR character recognition confidence verification
│   ├── test_pipeline.py            # End-to-end parser tests
│   └── test_segment.py             # Crop ROI boundary checks
│
├── server.py                       # Flask server engine endpoint
├── parser.py                       # EasyOCR & template matching pipeline
└── DEV_NOTE.md                     # Brutal honesty dev notes & performance baselines
```

---

## 2. Release & Maintenance Checklist

During every major or minor update (e.g. V0.14.2 -> V0.14.3), the following pipeline **must** be executed sequentially:

### 📑 Step 1: Pre-Commit Quality Checks
- [ ] **Extension Review**:
  - Verify that no debug logs or heavy variables are remaining in `sampling_engine.js`.
  - Check that canvas preview frame renders are properly gated by the 1Hz throttle in `popup.js` to avoid IPC choke.
- [ ] **Timing Lock Calibration**:
  - Check `RAPID_LOCK_DURATION_MS` is set to the targeted cooldown lock.
  - Verify that the `NORMAL_INTERVAL_MS` is set to the targeted monitoring loop rate.

### 🧪 Step 2: Running Automated Regression Tests
- [ ] Run parser unit tests:
  ```powershell
  python -m unittest tests/test_pipeline.py
  ```
- [ ] Run segment test check:
  ```powershell
  python -m unittest tests/test_segment.py
  ```
- [ ] Verify that all test cases return `OK`. Do not commit code that breaks OCR or layout parsing.

### 📈 Step 3: Telemetry & State Validation
- [ ] Spin up the Flask server (`python server.py`).
- [ ] Connect the Chrome Extension and run a **1-minute validation test capture**.
- [ ] Run a test verification of:
  - **Knocks** (red weapon icons).
  - **Finishes** (white weapon icons).
  - **Zone/Special events** (no layout crash).
- [ ] Check `v0.14_telemetry.csv` and ensure:
  - There are zero `0.0ms` logging values for frames that ran OCR.
  - `GPU_Percent` values are being successfully gathered on the background thread.
- [ ] Verify that `v0.14_summary.json` correctly logs:
  - `active_ingest_minutes` matching the actual session duration.
  - `total_events_logged` matches only the actual written lines in `QL.csv` (excluding skipped layouts).

### 🏷️ Step 4: Version Control & Version Bump
- [ ] Update version in `chrome_extension/manifest.json`.
- [ ] Append version history details to `version_history/v0.14_history.md` (or the relevant active cycle).
- [ ] Update `DEV_NOTE.md` with:
  - Date and version number.
  - Telemetry summary benchmark metrics from the validation run.

### 🚀 Step 5: Git Commit & Push
- [ ] Run `git status` and verify that only intended files are changed.
- [ ] Stage all modifications (`git add .`).
- [ ] Commit with clean semantic commit messages, e.g.:
  ```bash
  git commit -m "feat(v0.14.x): brief description"
  ```
- [ ] Push to `origin main`.
