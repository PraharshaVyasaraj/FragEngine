import time
import requests
import base64
import cv2
import os
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_requests():
    base_dir = r"C:\FragEngine"
    samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
    
    # Load and encode sample image
    img_path = os.path.join(samples_dir, "SAMPLE_ZONE_FINISH_1T2I.png")
    if not os.path.exists(img_path):
        print(f"[ERROR] Sample image not found at {img_path}")
        return
        
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    b64_data = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"

    url = "http://127.0.0.1:5000/process"
    
    # Define tasks: Row 0 and Row 1 concurrently
    tasks = [
        {"image": b64_data, "row_index": 0},
        {"image": b64_data, "row_index": 1}
    ]
    
    def send_request(task):
        t_start = time.perf_counter()
        try:
            res = requests.post(url, json=task)
            latency = (time.perf_counter() - t_start) * 1000
            return res.status_code, res.json(), latency
        except Exception as e:
            return 500, str(e), (time.perf_counter() - t_start) * 1000

    print("[TEST] Launching 2 simultaneous requests...")
    t_total_start = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(send_request, tasks))
        
    total_elapsed = (time.perf_counter() - t_total_start) * 1000
    
    print(f"\n[TEST RESULT] Both requests completed in {total_elapsed:.2f} ms")
    for idx, (code, body, lat) in enumerate(results):
        print(f"Request {idx} (Row {tasks[idx]['row_index']}): Status {code} | Latency {lat:.2f} ms")
        print(f"  Response: {body}\n")

if __name__ == "__main__":
    test_concurrent_requests()
