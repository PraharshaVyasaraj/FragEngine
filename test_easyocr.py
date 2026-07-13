import easyocr
import cv2
import os

images = [
    "SAMPLE_ZONE_FINISH_1T2I.png",
    "SAMPLE_WEAPON_KNOCK_2T2I.png",
    "SAMPLE_FIST_FINISH_2T2I.png"
]

base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED\TRANING_FEED_SAMPLE"

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

for img_name in images:
    path = os.path.join(base_dir, img_name)
    img = cv2.imread(path)
    if img is None:
        continue
    
    # Run reader
    results = reader.readtext(img)
    
    print(f"\n--- {img_name} ---")
    for res in results:
        bbox, text, prob = res
        # bbox is [[top_left], [top_right], [bottom_right], [bottom_left]]
        x1, y1 = bbox[0]
        x2, y2 = bbox[2]
        print(f"  Detected Text: '{text}' at X1={x1}, Y1={y1}, X2={x2}, Y2={y2} (Confidence: {prob:.2f})")
