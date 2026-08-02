# FragEngine V0.13 — SESSION_0006 Baseline Report

> **Session**: SESSION_0006 | **Date**: 2026-07-13 | **Duration**: ~25 min live capture
> **Data points**: 13,602 hardware samples | **OCR events**: 662 fired

---

## 🖥️ Hardware Utilization (CPU & RAM)

| Metric | Value |
|--------|-------|
| **CPU Avg** | 35.0% |
| **CPU Peak** | 100.0% |
| **RAM Avg** | 4,509.9 MB |
| **RAM Peak** | 8,488.1 MB |

> [!WARNING]
> **CPU hitting 100% peak** is a critical finding. These spikes occur when EasyOCR's PyTorch model fires on a P-core burst. This is the primary bottleneck that V0.14 OpenVINO offload will fix.

> [!WARNING]
> **RAM peaking at 8.5GB** is higher than expected. The baseline average of ~4.5GB is acceptable (EasyOCR model weights in memory), but 8.5GB peaks suggest memory pressure during concurrent Chrome + Flask + PyTorch execution.

---

## ⏱️ Pipeline Latency Breakdown (OCR Events Only)

| Stage | Avg | Median | Peak |
|-------|-----|--------|------|
| **OCR (EasyOCR)** | 2,456.8 ms | 2,055.6 ms | 10,390.3 ms |
| **Full Pipeline** | 2,496.4 ms | — | 10,398.9 ms |

> [!CAUTION]
> **OCR average of ~2.5 seconds is the confirmed bottleneck**. At this latency, the system can only reliably process ~0.4 OCR events per second. Kill feed events that appear and disappear in under 2 seconds may be missed entirely.
> The 10.4 second peak spike confirms that under CPU saturation (100%), PyTorch completely stalls.

---

## ✅ Quality Metrics (Gating & Deduplication)

| Metric | Value |
|--------|-------|
| **OCR Events Fired** | 662 |
| **Dict Corrections Applied** | 167 |
| **Suppressed Duplicates** | 409 |
| **Deduplication Rate** | ~61.8% |

> [!NOTE]
> The pixel-difference gate is working well — 662 frames actually broke through and hit the server out of what would have been thousands of raw frames at 30FPS over 25 minutes. The deduplication engine then further filtered 409 of those as duplicates, meaning only ~253 unique kill events were logged. Dictionary correction was applied 167 times (~67% of unique events), showing the auto-correction engine is highly active.

---

## 🎯 V0.14 OpenVINO Targets (Derived from This Baseline)

| Target | Current (V0.13 CPU) | Goal (V0.14 iGPU) |
|--------|--------------------|--------------------|
| **OCR Avg Latency** | 2,456.8 ms | < 100 ms |
| **OCR Peak Latency** | 10,390.3 ms | < 300 ms |
| **CPU Peak** | 100% | < 20% |
| **RAM Peak** | 8,488 MB | < 5,500 MB |

---

## 📌 Summary

The V0.13 CPU baseline confirms that **EasyOCR on CPU is the single critical bottleneck**. With OCR consuming 98.4% of the total pipeline time (2,456ms out of 2,496ms), all other stages (`decode`, `preprocess`, `icon_match`, `dict_correction`) are effectively free.

**V0.14 plan**: Convert EasyOCR CRAFT + CRNN models to ONNX and compile for Intel UHD 770 iGPU via OpenVINO. Expected outcome: >95% reduction in OCR latency, CPU stays under 20%, and the pipeline can reliably catch sub-1-second kill feed events.
