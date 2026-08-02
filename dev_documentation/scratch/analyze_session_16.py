import csv

csv_path = r"C:\FragEngine\data\sessions\SESSION_0016\v0.14_telemetry.csv"

total_records = 0
active_records = 0

ocr_times = []
total_times = []
confidences = []
cpu_percentages = []
ram_usages = []
gpu_percentages = []

with open(csv_path, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_records += 1
        latency = float(row["Total_Latency_ms"])
        if latency > 0:
            active_records += 1
            ocr_times.append(float(row["OCR_ms"]))
            total_times.append(latency)
            confidences.append(float(row["OCR_Confidence_Avg"]))
            cpu_percentages.append(float(row["CPU_Percent"]))
            ram_usages.append(float(row["RAM_MB"]))
            gpu_percentages.append(float(row["GPU_Percent"]))

print("=== SESSION 0016 Telemetry Analysis ===")
print(f"Total Log Records: {total_records}")
print(f"Active Processing Frames: {active_records}")
if active_records > 0:
    print(f"Avg OCR Latency: {sum(ocr_times)/active_records:.2f} ms")
    print(f"Avg Total Latency: {sum(total_times)/active_records:.2f} ms")
    print(f"Max OCR Latency: {max(ocr_times):.2f} ms")
    print(f"Avg OCR Confidence: {sum(confidences)/active_records:.4f}")
    print(f"Avg CPU load: {sum(cpu_percentages)/active_records:.2f} %")
    print(f"Avg RAM usage: {sum(ram_usages)/active_records:.2f} MB")
    print(f"Avg GPU load: {sum(gpu_percentages)/active_records:.2f} %")
else:
    print("No active frames found in logs.")
