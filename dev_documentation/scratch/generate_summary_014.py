import csv
import json
import statistics
import datetime
import os

csv_path = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0014\v0.14_telemetry.csv'
json_path = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0014\v0.14_summary.json'

if not os.path.exists(csv_path):
    print("CSV file not found!")
    exit(1)

rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

if not rows:
    print("No data in CSV!")
    exit(0)

# Filter rows that represent request events (latency total > 0)
ocr_rows = [r for r in rows if float(r['Total_Latency_ms']) > 0]

cpu = [float(r['CPU_Percent']) for r in rows]
ram = [float(r['RAM_MB']) for r in rows]
gpu = [float(r['GPU_Percent']) for r in rows]

ocr_ms = [float(r['OCR_ms']) for r in ocr_rows]
total_ms = [float(r['Total_Latency_ms']) for r in ocr_rows]
ocr_conf = [float(r['OCR_Confidence_Avg']) for r in ocr_rows if float(r['OCR_Confidence_Avg']) > 0]
lev_dist = [float(r['Avg_Levenshtein_Dist']) for r in ocr_rows if float(r['Avg_Levenshtein_Dist']) > 0]

dict_hits = sum(int(r['Dict_Hits']) for r in ocr_rows)
suppressed = sum(int(r['Suppressed_Duplicates']) for r in ocr_rows)
logged_count = len(ocr_rows) - suppressed

# Reconstruct match durations (V0.14.1)
# Total process lifetime
t_proc_start = datetime.datetime.strptime(rows[0]['Timestamp'], "%Y-%m-%d %H:%M:%S.%f")
t_proc_end = datetime.datetime.strptime(rows[-1]['Timestamp'], "%Y-%m-%d %H:%M:%S.%f")
proc_duration_min = (t_proc_end - t_proc_start).total_seconds() / 60.0

# Active ingestion window (first request to last request)
if ocr_rows:
    t_active_start = datetime.datetime.strptime(ocr_rows[0]['Timestamp'], "%Y-%m-%d %H:%M:%S.%f")
    t_active_end = datetime.datetime.strptime(ocr_rows[-1]['Timestamp'], "%Y-%m-%d %H:%M:%S.%f")
    active_duration_sec = (t_active_end - t_active_start).total_seconds()
else:
    active_duration_sec = (t_proc_end - t_proc_start).total_seconds()

active_duration_min = active_duration_sec / 60.0

total_requests = len(ocr_rows)
effective_fps = total_requests / active_duration_sec if active_duration_sec > 0 else 0.0
throughput = logged_count / active_duration_min if active_duration_min > 0 else 0.0

summary = {
    "session_directory": os.path.dirname(csv_path),
    "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_events_processed": len(ocr_rows),
    "total_dictionary_corrections": dict_hits,
    "total_duplicates_blocked": suppressed,
    
    # Ingestion Window Metrics (V0.14.1)
    "server_lifetime_minutes": round(proc_duration_min, 2),
    "active_ingest_minutes": round(active_duration_min, 2),
    "effective_fps_received": round(effective_fps, 4),
    "throughput_events_per_min": round(throughput, 2),
    "total_requests_received": total_requests,
    "total_events_logged": logged_count,
    
    # Quality Metrics
    "average_ocr_confidence": round(statistics.mean(ocr_conf), 4) if ocr_conf else 0.0,
    "average_levenshtein_distance": round(statistics.mean(lev_dist), 2) if lev_dist else 0.0,
    
    "hardware": {
        "cpu_avg": round(statistics.mean(cpu), 1),
        "cpu_peak": max(cpu),
        "ram_avg_mb": round(statistics.mean(ram), 1),
        "ram_peak_mb": max(ram),
        "gpu_avg": round(statistics.mean(gpu), 1),
        "gpu_peak": max(gpu)
    },
    
    "average_latencies_ms": {
        "decode": round(statistics.mean([float(r['Decode_ms']) for r in ocr_rows]), 2) if ocr_rows else 0.0,
        "preprocess": round(statistics.mean([float(r['Preprocess_ms']) for r in ocr_rows]), 2) if ocr_rows else 0.0,
        "ocr": round(statistics.mean(ocr_ms), 2) if ocr_ms else 0.0,
        "icon_match": round(statistics.mean([float(r['IconMatch_ms']) for r in ocr_rows]), 2) if ocr_rows else 0.0,
        "dict_correction": round(statistics.mean([float(r['DictCorrection_ms']) for r in ocr_rows]), 2) if ocr_rows else 0.0,
        "total": round(statistics.mean(total_ms), 2) if total_ms else 0.0
    }
}

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=4)

print("SUMMARY GENERATED SUCCESSFULLY:")
print(json.dumps(summary, indent=2))
