# FragEngine — Complete Version Timeline

> **Project**: FragEngine (FragLab Analytics Suite)
> **Repository**: [github.com/PraharshaVyasaraj/FragEngine](https://github.com/PraharshaVyasaraj/FragEngine)
> **Tech Lead**: Antigravity AI

---

## V0.1 — Foundation
| Patch | Description |
|-------|-------------|
| **V0.1.0** | Initial commit. Core `parser.py` with EasyOCR + OpenCV template matching. Basic `server.py` Flask backend. Chrome extension (`content.js`, `popup.html`, `background.js`) for ROI-based video capture. |

---

## V0.11 — Pipeline Hardening
| Patch | Description |
|-------|-------------|
| **V0.11.0** | Pixel-difference gating (threshold 8.0) in `content.js` to suppress duplicate OCR calls. Grayscale preprocessing and upscaling pipeline in `parser.py`. Template matching against SF Feed Icons. `difflib.SequenceMatcher` deduplication with cooldown timer. |

---

## V0.12 — Repository Professionalization
| Patch | Description |
|-------|-------------|
| **V0.12.0** | Added MIT `LICENSE`. Created `.github/` templates (`bug_report.md`, `feature_request.md`, `PULL_REQUEST_TEMPLATE.md`, `CONTRIBUTING.md`). Pinned exact versions in `requirements.txt`. Moved 8 test/utility scripts from root into `tests/` folder. Patched `sys.path` imports. Added `.github/workflows/tests.yml` GitHub Actions CI. Dictionary auto-correction engine with 62 team tags + 269 player names loaded from `data/corrections/`. README overhaul with architecture diagram. |

---

## V0.13 — Research Observability & Metrics Engine *(Current)*
| Patch | Commit | Description |
|-------|--------|-------------|
| **V0.13.0** | `ada2cf9` | **Telemetry Engine** (`backend/telemetry.py`): Background thread samples CPU %, RAM MB, thread count, context switches every 500ms. **Stage Timers**: `time.perf_counter()` profiling for `decode`, `preprocess`, `ocr`, `icon_match`, `dict_correction`. **Session Export**: `atexit` + signal handlers write `v0.13_telemetry.csv` and `v0.13_summary.json` to `data/sessions/SESSION_xxxx/`. **Click-to-Default ROI**: Single click = centered `240x24px` box. **Expanded Separators**: `x` delimiter support. **Offline Benchmark** (`benchmark.py`). |
| **V0.13.1** | `ef83702` | **CI Pipeline Fix**: `pytest.skip()` guards on all 5 local integration tests for GitHub Actions. New `test_ci.py` lightweight CI test. Installed `pytest` locally. |
| **V0.13.2** | `f14edf0` | **ROI Auto-Lock Bug Fix**: ROI now auto-locks on `mouseup` in `content.js`, persists to `chrome.storage.local`, sends `calibration-locked` to background worker, and auto-closes overlay. Fixed `popup.js` to reflect auto-locked state. |

---

## V0.14 — *(Planned: Intel OpenVINO iGPU Acceleration)*
| Feature | Description |
|---------|-------------|
| OpenVINO Runtime | Export EasyOCR CRAFT/CRNN models to ONNX → compile for Intel UHD 770 iGPU |
| P-Core Thread Bounds | `torch.set_num_threads(6)` to match i5-14500 P-core count |
| Zero-Copy Inference | Unified LPDDR5 pointer sharing (no PCIe buffer copy) |
| Before/After Benchmark | Compare V0.13 CPU baseline vs V0.14 iGPU telemetry over 10-min sessions |

---

```mermaid
gantt
    title FragEngine Release Timeline
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section V0.1
    Foundation & Core Pipeline       :done, v01, 2026-07-04, 1d

    section V0.11
    Pipeline Hardening               :done, v011, 2026-07-04, 1d

    section V0.12
    Repo Professionalization         :done, v012, 2026-07-12, 1d

    section V0.13
    Telemetry & Metrics Engine       :done, v013, 2026-07-13, 1d
    CI Pipeline Fix (0.13.1)         :done, v0131, 2026-07-13, 1d
    ROI Auto-Lock Fix (0.13.2)       :done, v0132, 2026-07-13, 1d

    section V0.14
    OpenVINO iGPU Acceleration       :planned, v014, after v0132, 3d
```
