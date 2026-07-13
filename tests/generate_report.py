import os
import cv2
import numpy as np
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

def main():
    icons_dir = r"E:\Games Data\SF FEED ICONS"
    dirty_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED\Dirty set"
    output_path = r"C:\Users\Praharsha\.gemini\antigravity-ide\brain\7deace2b-865e-41d1-898c-c4076727238a\telemetry_analysis.md"
    
    parser = FeedParser(icons_dir)
    
    dirty_images = [
        "Screenshot 2026-05-25 172459.png",
        "Screenshot 2026-05-25 172509.png",
        "Screenshot 2026-05-25 174711.png",
        "Screenshot 2026-05-25 174715.png",
        "Screenshot 2026-05-25 174811.png",
        "Screenshot 2026-05-25 174819.png",
        "Screenshot 2026-05-25 174847.png"
    ]
    
    md_content = []
    md_content.append("# V1 Telemetry Extraction & Bounding Box Analysis\n")
    md_content.append("This document contains the detailed diagnostic report, OCR extractions, template matching scores, and gatekeeper decisions for the 7 screenshots in the **Dirty set**.\n")
    
    for img_name in dirty_images:
        path = os.path.join(dirty_dir, img_name)
        if not os.path.exists(path):
            continue
            
        img = cv2.imread(path)
        orig_h, orig_w, _ = img.shape
        
        # 3x upscale for OCR help
        img_upscaled = cv2.resize(img, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        h, w, _ = img_upscaled.shape
        gray = cv2.cvtColor(img_upscaled, cv2.COLOR_BGR2GRAY)
        
        results = parser.reader.readtext(img_upscaled)
        text_blocks = []
        for res in results:
            bbox, text, prob = res
            x1 = int(bbox[0][0])
            x2 = int(bbox[2][0])
            if (x2 - x1) > 10 and prob > 0.15:
                text_blocks.append({"text": text.strip(), "x1": x1, "x2": x2, "prob": prob})
                
        text_blocks = sorted(text_blocks, key=lambda b: b["x1"])
        
        md_content.append(f"## 🖼️ File: `{img_name}`\n")
        md_content.append(f"* **Original Resolution:** `{orig_w}x{orig_h}`")
        md_content.append(f"* **OCR Bounding Box Count:** `{len(text_blocks)}` found")
        
        if len(text_blocks) == 0:
            md_content.append("\n> [!WARNING]")
            md_content.append("> **The Wall Status: BLOCKED** (No text components found). The crop is too low-resolution for the OCR network.")
            md_content.append("\n---\n")
            continue
            
        if len(text_blocks) == 2:
            layout = "2T2I"
            t1, t2 = text_blocks[0]["text"], text_blocks[1]["text"]
            icon_x1, icon_x2 = text_blocks[0]["x2"], text_blocks[1]["x1"]
        elif len(text_blocks) == 1:
            layout = "1T2I"
            t1, t2 = text_blocks[0]["text"], "None"
            icon_x1, icon_x2 = text_blocks[0]["x2"], w
        else:
            md_content.append("\n> [!WARNING]")
            md_content.append(f"> **The Wall Status: BLOCKED** (Unrecognized layout structure - found {len(text_blocks)} text blocks).")
            md_content.append("\n---\n")
            continue
            
        # Segment icons
        icon_band_gray = gray[:, icon_x1:icon_x2]
        _, thresh = cv2.threshold(icon_band_gray, 180, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        icon_crops = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw > 5 and ch > 5:
                crop = thresh[y:y+ch, x:x+cw]
                icon_crops.append((x, crop))
                
        icon_crops = sorted(icon_crops, key=lambda ic: ic[0])
        extracted_icons = [ic[1] for ic in icon_crops]
        
        md_content.append(f"* **Classified Layout:** `{layout}`")
        md_content.append(f"* **T1 (Attacker/Victim Name):** `{t1}`")
        md_content.append(f"* **T2 (Victim Name):** `{t2}`")
        
        i1_name, i1_score = "UNKNOWN", -1.0
        i2_name, i2_score = "UNKNOWN", -1.0
        
        scores_i1 = {}
        scores_i2 = {}
        
        if layout == "2T2I":
            i1_name = "Weapon"
            if len(extracted_icons) >= 1:
                state_crop = extracted_icons[-1]
                # Collect scores for KNOCK and FINISH
                for state in ["KNOCK", "FINISH"]:
                    _, score = parser.match_icon(state_crop, [state])
                    scores_i2[state] = score
                i2_name, i2_score = parser.match_icon(state_crop, ["KNOCK", "FINISH"])
        elif layout == "1T2I":
            if len(extracted_icons) >= 2:
                # Icon 1 (Hazard) scores
                for hazard in ["ZONE", "FALL", "DROWN"]:
                    _, score = parser.match_icon(extracted_icons[0], [hazard])
                    scores_i1[hazard] = score
                i1_name, i1_score = parser.match_icon(extracted_icons[0], ["ZONE", "FALL", "DROWN"])
                
                # Icon 2 (State) scores
                for state in ["KNOCK", "FINISH"]:
                    _, score = parser.match_icon(extracted_icons[1], [state])
                    scores_i2[state] = score
                i2_name, i2_score = parser.match_icon(extracted_icons[1], ["KNOCK", "FINISH"])
            elif len(extracted_icons) == 1:
                for state in ["KNOCK", "FINISH"]:
                    _, score = parser.match_icon(extracted_icons[0], [state])
                    scores_i2[state] = score
                i2_name, i2_score = parser.match_icon(extracted_icons[0], ["KNOCK", "FINISH"])
                
        # Format matching report
        md_content.append("\n### 🏷️ Icon Match Details")
        if layout == "2T2I":
            md_content.append(f"* **Icon 1 (Weapon):** Hardcoded to `Weapon` for V1")
        else:
            md_content.append(f"* **Icon 1 (Hazard):** Matched as `{i1_name}` (Score: `{i1_score:.4f}`)")
            if scores_i1:
                md_content.append("  * *Details:* " + ", ".join([f"`{k}`: `{v:.4f}`" for k, v in scores_i1.items()]))
                
        md_content.append(f"* **Icon 2 (State):** Matched as `{i2_name}` (Score: `{i2_score:.4f}`)")
        if scores_i2:
            md_content.append("  * *Details:* " + ", ".join([f"`{k}`: `{v:.4f}`" for k, v in scores_i2.items()]))
            
        # Gatekeeper Wall Decision
        is_valid = True
        reason = ""
        
        # Validation checks
        if not t1 or t1 == "None":
            is_valid = False
            reason = "OCR failed to read T1"
        elif layout == "2T2I" and (not t2 or t2 == "None"):
            is_valid = False
            reason = "OCR failed to read T2 in PvP event"
        elif i2_score < 0.65:
            is_valid = False
            reason = f"Icon 2 Match score ({i2_score:.2f}) below 0.65 threshold"
            
        if is_valid:
            md_content.append("\n> [!NOTE]")
            md_content.append(f"> **The Wall Status: PASSED**")
            md_content.append(f"> **QL Telemetry Entry:** `Log # | {layout} | {t1} | {i1_name} | {i2_name} | {t2}`")
        else:
            md_content.append("\n> [!WARNING]")
            md_content.append(f"> **The Wall Status: BLOCKED** (Reason: {reason})")
            
        md_content.append("\n---\n")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print("Report generated successfully at telemetry_analysis.md!")

if __name__ == "__main__":
    main()
