import os
import cv2
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser


def main():
    # Setup paths
    base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED"
    samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
    icons_dir = r"E:\Games Data\SF FEED ICONS"
    ql_path = os.path.join(base_dir, "QL.csv")
    
    # Initialize parser
    print("Initializing Feed Parser...")
    parser = FeedParser(icons_dir)
    
    # Setup the Quality Log file
    with open(ql_path, "w", encoding="utf-8") as f:
        f.write("Log # | Layout Type | T1 | I1 | I2 | T2\n")
        
    print(f"Created clean Quality Log at {ql_path}\n")
    
    # The Wall State Tracking
    last_log_entry = None
    log_counter = 1
    
    # Process sample files (simulating a stream of incoming events)
    images = [
        "SAMPLE_ZONE_FINISH_1T2I.png",
        "SAMPLE_WEAPON_KNOCK_2T2I.png",
        "SAMPLE_FIST_FINISH_2T2I.png"
    ]
    
    for img_name in images:
        path = os.path.join(samples_dir, img_name)
        print(f"Processing frame: {img_name}...")
        img = cv2.imread(path)
        
        # 1. Parse Frame
        res = parser.process_frame(img)
        
        # 2. Check "The Wall" (Gatekeeping)
        if res is None:
            print("  [WALL BLOCKED]: Frame is empty or unrecognizable.")
            continue
            
        # OCR Sanity Check
        if not res["t1"] or res["t1"] == "None":
            print(f"  [WALL BLOCKED]: Missing critical text for T1.")
            continue
            
        # Deduplication Check
        current_entry = (res["layout"], res["t1"], res["i1"], res["i2"], res["t2"])
        if current_entry == last_log_entry:
            print(f"  [WALL BLOCKED]: Duplicate event skipped.")
            continue
            
        # 3. Write to Quality Log (QL)
        last_log_entry = current_entry
        log_line = f"Log {log_counter} | {res['layout']} | {res['t1']} | {res['i1']} | {res['i2']} | {res['t2']}\n"
        
        with open(ql_path, "a", encoding="utf-8") as f:
            f.write(log_line)
            
        print(f"  [WALL PASSED] -> Added to QL: {log_line.strip()}")
        log_counter += 1
        
    print("\n--- Final Quality Log (QL.csv) Content ---")
    with open(ql_path, "r", encoding="utf-8") as f:
        print(f.read())

if __name__ == "__main__":
    main()
