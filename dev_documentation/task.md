# V0.14 Task List — Browser-First Event Detection Architecture

## Phase 1: V0.14.0 Core Architecture (Complete)

### Browser Modules
- [x] `feed_detector.js` — Color saturation icon detection
- [x] `sampling_engine.js` — Normal/Rapid state machine
- [x] `transmission_scheduler.js` — 800ms send throttle
- [x] `content.js` — Refactor: remove fixed FPS, expose grabFrame service
- [x] `background.js` — Refactor: remove captureTick, delegate to sampling engine
- [x] `manifest.json` — Bump to 0.14, register new content scripts
- [x] `popup.html` — Redesign as live diagnostics dashboard
- [x] `popup.js` — Real-time diagnostic field updates
- [x] `popup.css` — Diagnostic dashboard styling

### Backend Metrics
- [x] `parser.py` — Expose OCR confidence scores
- [x] `server.py` — Add Levenshtein distance, session counters
- [x] `backend/telemetry.py` — GPU%, session summary fields
- [x] `requirements.txt` — Add python-Levenshtein

---

## Phase 1.1: V0.14.1 Tuning & Refinements (Complete)
- [x] `chrome_extension/feed_detector.js` — Set `ICON_PIXEL_RATIO = 0.005`, `SATURATION_THRESHOLD = 0.25`
- [x] `chrome_extension/sampling_engine.js` — Set `NORMAL_INTERVAL_MS = 400`, implement 15-second "Fight Window" lock
- [x] `parser.py` — Return timings on unrecognizable layout
- [x] `server.py` — Log timings on skipped unrecognizable frame
- [x] `backend/telemetry.py` — Calculate summary statistics using active request window
- [x] `chrome_extension/manifest.json` — Bump to 0.14.1

---

## Phase 2: V0.14.1 Verification (Complete)
- [x] 3–4 minute validation session
- [x] Verify 100% fight window capture rate
- [x] Confirm layout timings logged properly in CSV
- [x] Update DEV_NOTE.md with V0.14.1 telemetry reports

---

## Phase 3: V0.14.2 Ingestion & State Overrides (Complete)
- [x] `chrome_extension/feed_detector.js` — Grayscale binarization CV gate (3%-30%)
- [x] `chrome_extension/sampling_engine.js` — Tune lock cooldown to 1.5s, throttle previews to 1Hz
- [x] `chrome_extension/popup.js` & `popup.html` — Add SUSPENDED state and density labels
- [x] `backend/telemetry.py` & `server.py` — Pass and track status categorization counters
- [x] `RELEASE_CHECKLIST.md` — Compile root operational guide and workflows
- [x] `SESSION_0010` validation run — 5.6 minutes run, 100% finish event capture, correct JSON counts
- [x] `SESSION_0011` validation run — 1.8 minutes short run, validation of double sample space and metrics consistency

---

## Phase 4: V0.14.3 Duplicate Mitigation & Thread Locks (Complete)
- [x] `chrome_extension/content.js` — Auto-pad calibration crop by 20px horizontally
- [x] `chrome_extension/transmission_scheduler.js` — Implement client-side 95% binarized similarity check
- [x] `server.py` — Synchronize endpoints via `server_lock` threading locks
- [x] `server.py` — Implement 400ms temporal event rate limiter and state-based duplicate checks
- [x] `chrome_extension/manifest.json` — Bump version to `0.14.3`
- [x] Run automated regression test validations (`test_pipeline.py` & `test_segment.py`)
- [x] `SESSION_0014` validation run — 4.67 minutes Scarfall telemetry run, verifying 53% drop in server requests and 44% drop in CPU load

---

## Phase 5: V0.15 Ingestion Bump, PaddleOCR, OpenVINO & UI Overhaul (In Progress)
- `[ ]` `chrome_extension/transmission_scheduler.js` — Reduce `SEND_INTERVAL_MS` to 360ms
- `[ ]` `chrome_extension/sampling_engine.js` — Implement 10-second REST mode (2000ms loop)
- `[ ]` `chrome_extension/popup.html/.css/.js` — Overhaul theme grid and live diagnostic metrics panel
- `[ ]` `requirements.txt` — Swap `easyocr` for `paddleocr` and `openvino`
- `[ ]` `parser.py` — Replace EasyOCR parser with PaddleOCR, implement ONNX/OpenVINO FP16 device routing
- `[ ]` `parser.py` — Refine template matching hierarchy to map GRENADE and FIST icons correctly
- `[ ]` `server.py` — Update server parser handlers and OpenVINO JIT compilation warm-up
- `[ ]` `SESSION_0015` validation run — 5,000 requests per 30 mins limit check, <50ms latency verification




