import time
import os
import cv2
import numpy as np

def run_openvino_comparison():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics package is not installed.")
        return
        
    base_dir = r"C:\FragEngine"
    icon_path = os.path.join(base_dir, "icons", "STATES", "KNOCK.png")
    if not os.path.exists(icon_path):
        print(f"[ERROR] Sample icon not found at {icon_path}")
        return
        
    print("=" * 60)
    print("   YOLOv8 NANO: PYTORCH CPU VS OPENVINO BENCHMARK")
    print("=" * 60)
    
    # 1. Load PyTorch model
    print("[INFO] Loading PyTorch YOLOv8 Nano model...")
    pt_model = YOLO("yolov8n.pt")
    
    # 2. Export to OpenVINO format (if not already exported)
    openvino_path = "yolov8n_openvino_model"
    if not os.path.exists(openvino_path):
        print("[INFO] Exporting PyTorch model to OpenVINO format...")
        pt_model.export(format="openvino")
    else:
        print("[INFO] OpenVINO model folder already exists.")
        
    # 3. Load OpenVINO model
    print("[INFO] Loading OpenVINO YOLOv8 Nano model...")
    ov_model = YOLO(openvino_path)
    
    # Preprocess image
    img = cv2.imread(icon_path)
    img_resized = cv2.resize(img, (256, 256))
    
    # Warm-up PyTorch
    print("[INFO] Warming up PyTorch CPU...")
    for _ in range(5):
        _ = pt_model(img_resized, device="cpu", verbose=False)
        
    # Warm-up OpenVINO
    print("[INFO] Warming up OpenVINO CPU...")
    for _ in range(5):
        _ = ov_model(img_resized, verbose=False)
        
    iterations = 30
    
    # Benchmark PyTorch CPU
    print(f"[INFO] Benchmarking PyTorch CPU ({iterations} runs)...")
    pt_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = pt_model(img_resized, device="cpu", verbose=False)
        pt_latencies.append((time.perf_counter() - t0) * 1000)
        
    # Benchmark OpenVINO CPU
    print(f"[INFO] Benchmarking OpenVINO CPU ({iterations} runs)...")
    ov_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = ov_model(img_resized, verbose=False)
        ov_latencies.append((time.perf_counter() - t0) * 1000)
        
    pt_latencies = np.array(pt_latencies)
    ov_latencies = np.array(ov_latencies)
    
    print("\n" + "="*50)
    print("            BENCHMARK RESULTS")
    print("="*50)
    print(f"PyTorch CPU Latency  : Mean: {pt_latencies.mean():.2f} ms | Min: {pt_latencies.min():.2f} ms | Max: {pt_latencies.max():.2f} ms")
    print(f"OpenVINO CPU Latency : Mean: {ov_latencies.mean():.2f} ms | Min: {ov_latencies.min():.2f} ms | Max: {ov_latencies.max():.2f} ms")
    print("-" * 50)
    speedup = pt_latencies.mean() / ov_latencies.mean()
    print(f"Speedup Factor       : {speedup:.2f}x faster with OpenVINO!")
    print("="*50)

if __name__ == "__main__":
    run_openvino_comparison()
