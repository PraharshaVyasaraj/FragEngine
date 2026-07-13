import cv2
import numpy as np
import os
import pytest

# Skip in CI since it depends on local gitignored assets
if os.environ.get("GITHUB_ACTIONS") == "true":
    pytest.skip("Skipping local integration tests in CI environment", allow_module_level=True)

images = [
    "SAMPLE_ZONE_FINISH_1T2I.png",
    "SAMPLE_WEAPON_KNOCK_2T2I.png",
    "SAMPLE_FIST_FINISH_2T2I.png"
]

base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED\TRANING_FEED_SAMPLE"

for k_size in [5, 7]:
    print(f"\n=================== TESTING KERNEL SIZE: ({k_size}, 1) ===================")
    for img_name in images:
        path = os.path.join(base_dir, img_name)
        img = cv2.imread(path)
        if img is None:
            continue
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, 1))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rects = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 5 and h > 5:
                rects.append((x, y, w, h))
                
        rects = sorted(rects, key=lambda r: r[0])
        
        print(f"\n--- {img_name} ---")
        print(f"Total components detected: {len(rects)}")
        for i, (x, y, w, h) in enumerate(rects):
            aspect_ratio = w / float(h)
            print(f"  Component {i}: X={x}, Y={y}, W={w}, H={h}, Aspect Ratio={aspect_ratio:.2f}")
