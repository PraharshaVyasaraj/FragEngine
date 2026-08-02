import csv
import statistics
import os

csv_0008 = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0008\v0.14_telemetry.csv'
csv_0009 = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0009\v0.14_telemetry.csv'

def print_hardware_stats(csv_path, session_name):
    if not os.path.exists(csv_path):
        print(f"{session_name} CSV not found!")
        return
    cpu, ram, gpu = [], [], []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            cpu.append(float(r['CPU_Percent']))
            ram.append(float(r['RAM_MB']))
            gpu.append(float(r['GPU_Percent']))
    print(f"\n--- {session_name} HARDWARE STATS ---")
    print(f"CPU Avg: {statistics.mean(cpu):.1f}% | Peak: {max(cpu):.1f}%")
    print(f"RAM Avg: {statistics.mean(ram):.1f}MB | Peak: {max(ram):.1f}MB")
    print(f"GPU Avg: {statistics.mean(gpu):.1f}% | Peak: {max(gpu):.1f}%")
    print(f"Total telemetry data points: {len(cpu)}")

print_hardware_stats(csv_0008, "SESSION_0008 (V0.14.0)")
print_hardware_stats(csv_0009, "SESSION_0009 (V0.14.1)")
