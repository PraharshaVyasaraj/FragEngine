import cv2
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

def run_recognition_test():
    base_dir = r"C:\FragEngine"
    samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
    icons_dir = os.path.join(base_dir, "icons")
    
    parser = FeedParser(icons_dir)
    images = ["SAMPLE_ZONE_FINISH_1T2I.png", "SAMPLE_WEAPON_KNOCK_2T2I.png", "SAMPLE_FIST_FINISH_2T2I.png"]
    
    print("="*60)
    print("        FRAGENGINE ACTIVE RECOGNITION TEST RUN")
    print("="*60)
    
    for img_name in images:
        p = os.path.join(samples_dir, img_name)
        if not os.path.exists(p):
            print(f"[ERROR] Missing sample image: {p}")
            continue
            
        img = cv2.imread(p)
        res = parser.process_frame(img)
        
        print(f"\nImage: {img_name}")
        print(f"  |- Layout Classified : {res.get('layout')}")
        print(f"  |- Text Detections   : T1='{res.get('t1')}' | T2='{res.get('t2')}'")
        print(f"  |- Icon 1 Recognized : '{res.get('i1')}' (Confidence: {res.get('i1_confidence'):.4f})")
        print(f"  |- Icon 2 Recognized : '{res.get('i2')}' (Confidence: {res.get('i2_confidence'):.4f})")
        print(f"  |- Latency Timings   : OCR: {res['_timings']['ocr']:.1f}ms | IconMatch: {res['_timings']['icon_match']:.1f}ms")
    print("="*60)

if __name__ == "__main__":
    run_recognition_test()
