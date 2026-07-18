import os
import cv2
import base64
import time
import requests
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Target server URL
URL = "http://127.0.0.1:5000/process"

# Load sample image
base_dir = r"C:\FragEngine"
sample_path = os.path.join(base_dir, "TRANING_FEED_SAMPLE", "SAMPLE_WEAPON_KNOCK_2T2I.png")

if not os.path.exists(sample_path):
    print(f"Error: Sample image not found at {sample_path}")
    exit(1)

img = cv2.imread(sample_path)
_, buffer = cv2.imencode('.jpg', img)
base64_jpg = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

payload = {"image": base64_jpg}

def send_request(req_id):
    t0 = time.perf_counter()
    try:
        res = requests.post(URL, json=payload, timeout=10)
        latency = (time.perf_counter() - t0) * 1000
        
        # Check if the server response is logged/duplicate/skipped
        status = "unknown"
        if res.status_code == 200:
            status = res.json().get("status", "no_status")
        else:
            status = f"HTTP_{res.status_code}"
            
        return req_id, latency, status
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return req_id, latency, f"Error: {e}"

print("=" * 60)
print("FRAGENGINE V0.16 CONCURRENCY BENCHMARK")
print("Evaluating Multi-Threaded Flask + Decoupled Standby Pools")
print("=" * 60)

# Pre-warm: Send a single request to initialize models
print("Pre-warming server connection...")
_, w_lat, w_status = send_request(0)
print(f"Warm-up request finished. Latency: {w_lat:.1f}ms, Status: {w_status}")

# Run Benchmark: Send 5 concurrent requests
concurrency_factor = 5
print(f"\nSending {concurrency_factor} concurrent requests simultaneously...")

t_start = time.perf_counter()
with ThreadPoolExecutor(max_workers=concurrency_factor) as ex:
    results = list(ex.map(send_request, range(1, concurrency_factor + 1)))
total_elapsed_ms = (time.perf_counter() - t_start) * 1000

print("\n--- RESULTS ---")
latencies = []
for req_id, latency, status in results:
    latencies.append(latency)
    print(f"  Request #{req_id:<2} : Latency: {latency:>6.1f}ms | Status: {status}")

latencies = np.array(latencies)
print("\n--- STATISTICAL DISTRIBUTION (ms) ---")
print(f"  Min       : {latencies.min():.1f}ms")
print(f"  P25       : {np.percentile(latencies, 25):.1f}ms")
print(f"  P50 (Med) : {np.percentile(latencies, 50):.1f}ms")
print(f"  Mean      : {latencies.mean():.1f}ms")
print(f"  P90       : {np.percentile(latencies, 90):.1f}ms")
print(f"  P99       : {np.percentile(latencies, 99):.1f}ms")
print(f"  Max       : {latencies.max():.1f}ms")
print(f"  Stddev    : {latencies.std():.1f}ms")

print(f"\nTotal elapsed time for all {concurrency_factor} requests: {total_elapsed_ms:.1f}ms")
print(f"Theoretical serialized time: {latencies.sum():.1f}ms")
concurrency_efficiency = (latencies.sum() / total_elapsed_ms)
print(f"Concurrency Efficiency: {concurrency_efficiency:.2f}x speedup")

# Check if port 5000 blocked
if total_elapsed_ms < latencies.sum() * 0.8:
    print("\n[VERDICT] SUCCESS: Flask is handling requests in parallel (No blocking queue)!")
else:
    print("\n[VERDICT] WARNING: Concurrency speedup is low. Check CPU threads contention.")
