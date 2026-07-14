import os
import cv2
import time
import numpy as np
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

def run_benchmark():
    icons_dir = r"C:\FragEngine\icons"
    base_dir = r"C:\FragEngine"
    
    # Initialize parser
    print("====================================================")
    print(" Initializing PP-OCRv5 Mobile + Template Matcher... ")
    print("====================================================")
    t0 = time.perf_counter()
    parser = FeedParser(icons_dir)
    print(f"Warm-up took {time.perf_counter() - t0:.2f} seconds.\n")
    
    # Define datasets and their expected ground-truths
    # Ground truth format: (expected_layout, expected_i1_action, expected_i2_state)
    ground_truths = {
        # Training set samples
        "SAMPLE_ZONE_FINISH_1T2I.png": ("1T2I", "ZONE", "FINISH"),
        "SAMPLE_WEAPON_KNOCK_2T2I.png": ("2T2I", "Weapon", "KNOCK"),
        "SAMPLE_FIST_FINISH_2T2I.png": ("2T2I", "FIST", "FINISH"),
    }
    
    ocr_latencies = []
    match_latencies = []
    total_latencies = []
    
    correct_layouts = 0
    correct_actions = 0
    correct_states = 0
    total_evals = 0
    
    # Warm-up the OpenVINO compiler (run 5 times on the first image to load layers into iGPU)
    first_img_name = list(ground_truths.keys())[0]
    first_path = os.path.join(os.path.join(base_dir, "TRANING_FEED_SAMPLE"), first_img_name)
    if os.path.exists(first_path):
        warmup_img = cv2.imread(first_path)
        if warmup_img is not None:
            print("Warming up OpenVINO GPU execution layers...")
            warmup_upscaled = cv2.resize(warmup_img, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            for _ in range(5):
                parser.process_frame(warmup_upscaled)
            print("Warm-up complete!\n")

    print("| Image Name | Layout | Avg OCR Latency | Icon Match | Total Latency | I1 (Action) | I2 (State) | Status |")
    print("|---|---|---|---|---|---|---|---|")
    
    # Run over training samples
    samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
    dirty_dir = os.path.join(base_dir, "Dirty set")
    
    for filename, gt in ground_truths.items():
        # Determine correct path
        path = os.path.join(samples_dir, filename)
        if not os.path.exists(path):
            path = os.path.join(dirty_dir, filename)
            
        if not os.path.exists(path):
            continue
            
        img = cv2.imread(path)
        if img is None:
            continue
            
        # Run 5 times and take average of the last 4 runs to get steady-state latency
        runs_ocr = []
        runs_match = []
        last_res = None
        
        # Apply 1.5x resize scale to match production server.py exactly
        img_upscaled = cv2.resize(img, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        
        for i in range(5):
            res = parser.process_frame(img_upscaled)
            if i > 0: # Skip first run to avoid residual JIT compiler spikes
                runs_ocr.append(res["_timings"]["ocr"])
                runs_match.append(res["_timings"]["icon_match"])
            last_res = res
            
        ocr_ms = np.mean(runs_ocr)
        match_ms = np.mean(runs_match)
        total_ms = ocr_ms + match_ms
        
        ocr_latencies.append(ocr_ms)
        match_latencies.append(match_ms)
        total_latencies.append(total_ms)
        
        total_evals += 1
        
        # Verify predictions
        pred_layout = last_res.get("layout", "unrecognizable")
        pred_i1 = last_res.get("i1", "UNKNOWN")
        pred_i2 = last_res.get("i2", "UNKNOWN")
        
        exp_layout, exp_i1, exp_i2 = gt
        
        layout_ok = pred_layout == exp_layout
        i1_ok = pred_i1 == exp_i1
        i2_ok = pred_i2 == exp_i2
        
        if layout_ok: correct_layouts += 1
        if i1_ok: correct_actions += 1
        if i2_ok: correct_states += 1
        
        overall_status = "PASS" if (layout_ok and i1_ok and i2_ok) else "FAIL"
        
        print(f"| {filename} | {pred_layout} | {ocr_ms:.1f}ms (steady) | {match_ms:.1f}ms | {total_ms:.1f}ms | {pred_i1} | {pred_i2} | {overall_status} |")
        
    print("\n====================================================")
    print("                 BENCHMARK SUMMARY                  ")
    print("====================================================")
    print(f"Total evaluated frames  : {total_evals}")
    print(f"Layout accuracy         : {correct_layouts}/{total_evals} ({correct_layouts/total_evals*100:.1f}%)")
    print(f"Icon Action accuracy    : {correct_actions}/{total_evals} ({correct_actions/total_evals*100:.1f}%)")
    print(f"Icon State accuracy     : {correct_states}/{total_evals} ({correct_states/total_evals*100:.1f}%)")
    print("----------------------------------------------------")
    print(f"Average OCR Latency     : {np.mean(ocr_latencies):.2f} ms")
    print(f"Average Icon Match      : {np.mean(match_latencies):.2f} ms")
    print(f"Average Total Latency   : {np.mean(total_latencies):.2f} ms")
    print("====================================================\n")

if __name__ == "__main__":
    run_benchmark()
