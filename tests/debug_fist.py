import cv2
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

icons_dir = r"C:\FragEngine\icons"
parser = FeedParser(icons_dir)

# Read the fist image
path = r"C:\FragEngine\TRANING_FEED_SAMPLE\SAMPLE_FIST_FINISH_2T2I.png"
img = cv2.imread(path)
h, w, _ = img.shape
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# OCR text blocks extraction
results = parser.ocr.ocr(img, cls=False)
page_results = results[0] if results and results[0] else []
text_blocks = []
for line in page_results:
    bbox, (text, prob) = line
    x1, x2 = int(bbox[0][0]), int(bbox[2][0])
    text_blocks.append({"text": text, "x1": x1, "x2": x2})
text_blocks = sorted(text_blocks, key=lambda b: b["x1"])

print("Text blocks:", text_blocks)

# Get coordinates
icon_x1 = text_blocks[0]["x2"]
icon_x2 = text_blocks[1]["x1"]

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

print(f"Extracted {len(extracted_icons)} icons.")

if len(extracted_icons) >= 2:
    action_crop = extracted_icons[0]
    # Match action crop against all templates and print scores
    for name in ["GRENADE", "VEHICLE", "FIST"]:
        tpl_list = parser.templates.get(name, [])
        print(f"\nCategory: {name} (Template count: {len(tpl_list)})")
        for i, tpl in enumerate(tpl_list):
            ch, cw = action_crop.shape
            tpl_resized = cv2.resize(tpl, (cw, ch))
            _, tpl_binary = cv2.threshold(tpl_resized, 127, 255, cv2.THRESH_BINARY)
            
            res = cv2.matchTemplate(action_crop, tpl_binary, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            print(f"  Template {i} Match Score: {max_val:.4f}")
