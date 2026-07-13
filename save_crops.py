import cv2
import numpy as np
import os

base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED"
samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
icons_dir = r"E:\Games Data\SF FEED ICONS"
output_dir = r"C:\Users\Praharsha\.gemini\antigravity-ide\brain\7deace2b-865e-41d1-898c-c4076727238a"

def load_template(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.shape[-1] == 4:
        alpha = img[:, :, 3]
        if alpha.min() < 255:
            return alpha
        else:
            return cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Save templates
for folder, name in [("STATES", "KNOCK.png"), ("STATES", "FINISH.png"), ("STATES", "FALL.png"), ("STATES", "DROWN.png"), ("ZONE", "ZONE.png")]:
    p = os.path.join(icons_dir, folder, name)
    if os.path.exists(p):
        tpl = load_template(p)
        cv2.imwrite(os.path.join(output_dir, f"debug_tpl_{name}"), tpl)

# Save crops from SAMPLE_ZONE_FINISH_1T2I.png
img_path = os.path.join(samples_dir, "SAMPLE_ZONE_FINISH_1T2I.png")
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
rects = []
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w > 5 and h > 5:
        rects.append((x, y, w, h))
rects = sorted(rects, key=lambda r: r[0])

# We only care about the last two components (the icons)
icon_idx = 1
for x, y, w, h in rects:
    if x > 160: # Only icons
        crop_gray = gray[y:y+h, x:x+w]
        crop_thresh = thresh[y:y+h, x:x+w]
        cv2.imwrite(os.path.join(output_dir, f"debug_crop_gray_{icon_idx}.png"), crop_gray)
        cv2.imwrite(os.path.join(output_dir, f"debug_crop_thresh_{icon_idx}.png"), crop_thresh)
        print(f"Saved icon crop {icon_idx} (x={x}, y={y}, w={w}, h={h})")
        icon_idx += 1
