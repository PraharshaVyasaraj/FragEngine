import os
import cv2
import numpy as np
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

def main():
    icons_dir = r"E:\Games Data\SF FEED ICONS"
    dirty_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED\Dirty set"
    
    # Initialize parser
    parser = FeedParser(icons_dir)
    
    # The 7 images inside the Dirty set folder
    dirty_images = [
        "Screenshot 2026-05-25 172459.png",
        "Screenshot 2026-05-25 172509.png",
        "Screenshot 2026-05-25 174711.png",
        "Screenshot 2026-05-25 174715.png",
        "Screenshot 2026-05-25 174811.png",
        "Screenshot 2026-05-25 174819.png",
        "Screenshot 2026-05-25 174847.png"
    ]
    
    print("=================== RUNNING DIRTY SET CONFIDENCE TEST (WITH 3X UPSCALE) ===================")
    
    for img_name in dirty_images:
        path = os.path.join(dirty_dir, img_name)
        if not os.path.exists(path):
            print(f"\nSkipping {img_name}: File not found.")
            continue
            
        img = cv2.imread(path)
        orig_h, orig_w, _ = img.shape
        
        # 1. Upscale the image 3x using cubic interpolation to helper OCR read tiny text
        img_upscaled = cv2.resize(img, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        
        h, w, _ = img_upscaled.shape
        gray = cv2.cvtColor(img_upscaled, cv2.COLOR_BGR2GRAY)
        
        # Run EasyOCR on upscaled image
        results = parser.reader.readtext(img_upscaled)
        text_blocks = []
        for res in results:
            bbox, text, prob = res
            x1 = int(bbox[0][0])
            x2 = int(bbox[2][0])
            if (x2 - x1) > 10 and prob > 0.15:
                text_blocks.append({"text": text.strip(), "x1": x1, "x2": x2, "prob": prob})
                
        text_blocks = sorted(text_blocks, key=lambda b: b["x1"])
        
        print(f"\n--- Frame: {img_name} (orig size: {orig_w}x{orig_h}) ---")
        print(f"  OCR Found: {[b['text'] for b in text_blocks]}")
        
        if len(text_blocks) == 2:
            layout = "2T2I"
            t1, t2 = text_blocks[0]["text"], text_blocks[1]["text"]
            icon_x1, icon_x2 = text_blocks[0]["x2"], text_blocks[1]["x1"]
        elif len(text_blocks) == 1:
            layout = "1T2I"
            t1, t2 = text_blocks[0]["text"], "None"
            icon_x1, icon_x2 = text_blocks[0]["x2"], w
        else:
            print("  [RESULT]: Skip/Layout Unknown (0 or >2 text blocks)")
            continue
            
        # Isolate the horizontal band containing the icons in the upscaled coordinates
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
        
        i1_name, i1_score = "UNKNOWN", 0.0
        i2_name, i2_score = "UNKNOWN", 0.0
        
        if layout == "2T2I":
            i1_name = "Weapon"
            if len(extracted_icons) >= 1:
                state_crop = extracted_icons[-1]
                i2_name, i2_score = parser.match_icon(state_crop, ["KNOCK", "FINISH"])
        elif layout == "1T2I":
            if len(extracted_icons) >= 2:
                i1_name, i1_score = parser.match_icon(extracted_icons[0], ["ZONE", "FALL", "DROWN"])
                i2_name, i2_score = parser.match_icon(extracted_icons[1], ["KNOCK", "FINISH"])
            elif len(extracted_icons) == 1:
                i2_name, i2_score = parser.match_icon(extracted_icons[0], ["KNOCK", "FINISH"])
                
        print(f"  [PARSED]: Layout={layout} | T1={t1} | I1={i1_name} (conf={i1_score:.2f}) | I2={i2_name} (conf={i2_score:.2f}) | T2={t2}")

if __name__ == "__main__":
    main()
