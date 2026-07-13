# GameVision Telemetry Engine (V0.12)

A high-performance, real-time telemetry extraction engine for streaming gameplay video feeds. Built as a hybrid system with a lightweight Google Chrome Side Panel frontend and a local PyTorch Flask backend, this engine extracts, normalizes, and filters BGMI/PUBG Mobile kill feed events with sub-33ms event detection latency.

---

## 🏗️ Architecture Design

```mermaid
graph TD
    subgraph Browser Context (Chrome Extension)
        A[HTML5 Video Element] -->|30 FPS Render| B(Diagnostic Preview Canvas)
        A -->|30 FPS Sampling| C{JS Raw Pixel Diff Gate}
        C -->|No Change| D[Skip Processing]
        C -->|Change Detected| E[Canvas toDataURL JPEG]
        E -->|HTTP POST| F[Flask API /process]
    end

    subgraph Backend Context (Python Server)
        F --> G[Decode Image]
        G --> H{Brightness Check}
        H -->|Bright UI Bleed| I[Block Frame]
        H -->|Dark Feed BG| J[3x Cubic Upscale]
        J --> K[EasyOCR Text Extraction]
        K --> L[OpenCV Template Matching]
        L --> M[Soft Dictionary Corrector]
        M --> N{Victim Cooldown Check}
        N -->|Locked| O[Block Duplicate]
        N -->|Unlocked| P{Fuzzy Deduplicator}
        P -->|Similarity >= 82%| Q[Block Duplicate]
        P -->|Approved| R[Save Cooldown Lock]
        R --> S[Append to QL.csv]
    end
```

---

## ⚡ Key Optimizations in V0.12

-   **JS-Side Raw Pixel Diffing**: Evaluates raw canvas pixel arrays directly in browser memory at 30 FPS. Skips JPEG compression and HTTP POST network overhead for 95% of frames, reducing client/server CPU footprint to virtually 0% during idle times.
-   **PyTorch Concurrency Limit**: Configured `torch.set_num_threads(8)` to utilize dedicated Performance cores, dropping OCR processing latency to `~20-30ms` without freezing other CPU tasks.
-   **Soft Dictionary Auto-Correction**: Fuzzy matches extracted team tags and player names against CSV databases (`Dataset/`). Misspelled known players are snapped (confidence $\ge 85\%$) while unknown player profiles are preserved in their raw OCR format.
-   **Fuzzy Deduplication & Cooldown**: Matches names across frames using Levenshtein similarity ratios ($\ge 82\%$) combined with a 3.5-second cooldown locked on `(T2 + I2)` to completely eliminate double-logging of OCR variations.

---

## 🛠️ Getting Started

### 1. Requirements & Dependencies
Ensure Python 3.10+ is installed on your system. Install the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Run the Telemetry Server
Open a terminal window and start the Flask engine:
```bash
cd "E:\Games Data\SAMPLE_IMAGESET_FEED"
$env:PYTHONIOENCODING="utf-8"; python server.py
```

### 3. Load the Extension
1. Open **Chrome** and navigate to `chrome://extensions/`.
2. Enable **Developer Mode** (top right toggle).
3. Click **Load unpacked** (top left) and select the `chrome_extension/` directory.
4. Open the Extension Side Panel, open your game stream, and click **Start Telemetry Ingest** (using the pre-configured default 240x24px crop!).

---

## 🏷️ Version History & Git Flow

We maintain explicit releases using Git tags. The version history log is preserved inside the `version_history/` directory:

-   **V0.1** ([v0.1_history.md](file:///E:/Games%20Data/SAMPLE_IMAGESET_FEED/version_history/v0.1_history.md)): Initial release.
-   **V0.11** ([v0.11_history.md](file:///E:/Games%20Data/SAMPLE_IMAGESET_FEED/version_history/v0.11/v0.11_history.md)): Stage 1 Python diff gate & 30 FPS pipeline.
-   **V0.12** ([v0.12_history.md](file:///E:/Games%20Data/SAMPLE_IMAGESET_FEED/version_history/v0.12/v0.12_history.md)): High-performance browser diff gate & dictionary correction.

To inspect tag releases:
```bash
git tag -n
```
