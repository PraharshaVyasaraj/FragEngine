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

results = parser.ocr.ocr(img, cls=False)
page_results = results[0] if results and results[0] else []
text_blocks = []
for line in page_results:
    bbox, (text, prob) = line
    x1, x2 = int(bbox[0][0]), int(bbox[2][0])
    text_blocks.append({"text": text, "x1": x1, "x2": x2})
text_blocks = sorted(text_blocks, key=lambda b: b["x1"])

icon_x1 = text_blocks[0]["x2"]
icon_x2 = text_blocks[1]["x1"]

icon_band_gray = gray[:, icon_x1:icon_x2]
_, thresh = cv2.threshold(icon_band_gray, 180, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
icon_crops = []
for c in contours:
    x, y, cw, ch = cv2.boundingRect(c)
    if cw >= 12 and ch >= 12:
        crop = thresh[y:y+ch, x:x+cw]
        icon_crops.append((x, crop))
icon_crops = sorted(icon_crops, key=lambda ic: ic[0])

# Save the extracted crops
cv2.imwrite(r"C:\FragEngine\tests\debug_extracted_fist_crop.png", icon_crops[0][1])

# Save the FIST template crop
fist_tpl = parser.templates["FIST"][0]
cv2.imwrite(r"C:\FragEngine\tests\debug_fist_template_crop.png", fist_tpl)

# Resize template to crop shape and save
ch, cw = icon_crops[0][1].shape
tpl_resized = cv2.resize(fist_tpl, (cw, ch))
_, tpl_binary = cv2.threshold(tpl_resized, 127, 255, cv2.THRESH_BINARY)
cv2.imwrite(r"C:\FragEngine\tests\debug_fist_template_resized.png", tpl_binary)

print("Saved debug images in C:\\FragEngine\\tests\\")
