import cv2
import numpy as np
import os

base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED"
samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
icons_dir = r"E:\Games Data\SF FEED ICONS"

# Check templates
print("--- Template Densities ---")
for folder, name in [("STATES", "KNOCK.png"), ("STATES", "FINISH.png"), ("STATES", "FALL.png"), ("STATES", "DROWN.png"), ("ZONE", "ZONE.png")]:
    p = os.path.join(icons_dir, folder, name)
    if not os.path.exists(p):
        continue
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img.shape[-1] == 4:
        alpha = img[:, :, 3]
        if alpha.min() < 255:
            mask = (alpha > 127).astype(np.uint8) * 255
        else:
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
    white_pixels = np.sum(mask == 255)
    total_pixels = mask.size
    print(f"{name}: shape={mask.shape}, white_pct={white_pixels/total_pixels:.2%}")

# Check sample image content and threshold
print("\n--- Sample Crops ---")
img_path = os.path.join(samples_dir, "SAMPLE_ZONE_FINISH_1T2I.png")
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

print("Grayscale min/max:", gray.min(), gray.max())
print("Thresholded white pixels:", np.sum(thresh == 255), "out of", thresh.size)

# Find contours
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for i, c in enumerate(contours):
    x, y, w, h = cv2.boundingRect(c)
    if w > 5 and h > 5:
        crop = thresh[y:y+h, x:x+w]
        white_pct = np.sum(crop == 255) / crop.size
        print(f"Contour {i}: x={x}, y={y}, w={w}, h={h}, white_pct={white_pct:.2%}")
