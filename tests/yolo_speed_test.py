import time
import os
import cv2
import numpy as np

def run_yolo_speed_test():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics package is not installed. Run yolo_training/train.py first.")
        return
        
    base_dir = r"C:\FragEngine"
    icon_path = os.path.join(base_dir, "icons", "STATES", "KNOCK.png")
    if not os.path.exists(icon_path):
        print(f"[ERROR] Sample icon not found at {icon_path}")
        return
        
    print("=" * 60)
    print("        YOLOv8 NANO ICON SPEED BENCHMARK")
    print("=" * 60)
    
    # 1. Load model (this downloads yolov8n.pt if not present)
    print("[INFO] Loading YOLOv8 Nano model weights...")
    model = YOLO("yolov8n.pt")
    
    # 2. Read and preprocess image
    img = cv2.imread(icon_path)
    # Resize to standard YOLO input size (256x256)
    img_resized = cv2.resize(img, (256, 256))
    
    # Warm-up iterations
    print("[INFO] Warming up inference engine (10 runs)...")
    for _ in range(10):
        _ = model(img_resized, device="cpu", verbose=False)
        
    # Benchmark iterations
    iterations = 50
    print(f"[INFO] Running {iterations} benchmark inference runs on CPU...")
    
    latencies = []
    for i in range(iterations):
        t_start = time.perf_counter()
        _ = model(img_resized, device="cpu", verbose=False)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000)
        
    latencies = np.array(latencies)
    
    print("\n--- INFERENCE LATENCY RESULTS (CPU) ---")
    print(f"  Min latency  : {latencies.min():.2f} ms")
    print(f"  Mean latency : {latencies.mean():.2f} ms")
    print(f"  Max latency  : {latencies.max():.2f} ms")
    print(f"  Median (P50) : {np.percentile(latencies, 50):.2f} ms")
    print(f"  P90 latency  : {np.percentile(latencies, 90):.2f} ms")
    print(f"  Throughput   : {1000 / latencies.mean():.1f} frames/sec")
    print("=" * 60)

if __name__ == "__main__":
    run_yolo_speed_test()
