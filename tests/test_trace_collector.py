import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cv2
import json
from parser import FeedParser

print("Initializing FeedParser for Trace Diagnostic Test...")
parser = FeedParser("icons")

print("\nProcessing SAMPLE_FIST_FINISH_2T2I.png...")
img = cv2.imread("TRANING_FEED_SAMPLE/SAMPLE_FIST_FINISH_2T2I.png")
img_upscaled = cv2.resize(img, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

res = parser.process_frame(img_upscaled)

print("\n--- OCR thought process trace successfully collected! ---")
print(f"Decided Layout: {res['layout']}")
print(f"Parsed T1 name: {res['t1']} | T2 name: {res['t2']}")

print(f"\nTotal Raw OCR boxes: {len(res['debug_trace']['raw_ocr'])}")
for idx, box in enumerate(res['debug_trace']['raw_ocr']):
    print(f"  [{idx}] '{box['text']}' with confidence {box['confidence']:.3f}")

print(f"\nIcon band coordinates: {res['debug_trace']['icon_band']}")

print(f"\nExtracted icon contours: {len(res['debug_trace']['contours'])}")
for idx, contour in enumerate(res['debug_trace']['contours']):
    print(f"  [{idx}] Box: {contour['x']},{contour['y']} size: {contour['width']}x{contour['height']} -> {contour['status']}")

# Find top matching correlation evaluations
print("\nTop 5 Template Match Correlations Checked:")
sorted_evals = sorted(res['debug_trace']['template_evaluations'], key=lambda e: e['score'], reverse=True)
for ev in sorted_evals[:5]:
    print(f"  Category: {ev['category']} | Threshold: {ev['threshold']} | Scale: {ev['scale']} | Correlation Score: {ev['score']:.4f}")
