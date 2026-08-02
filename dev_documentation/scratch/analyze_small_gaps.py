import csv
import datetime
import os

csv_path = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0008\v0.14_telemetry.csv'

if not os.path.exists(csv_path):
    print("CSV not found!")
    exit(1)

rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

reqs = [r for r in rows if float(r['Total_Latency_ms']) > 0]
timestamps = [datetime.datetime.strptime(r['Timestamp'], "%Y-%m-%d %H:%M:%S.%f") for r in reqs]

deltas = []
for i in range(1, len(timestamps)):
    delta = (timestamps[i] - timestamps[i-1]).total_seconds()
    deltas.append(delta)

# Analyze small gaps distribution
below_1_2 = [d for d in deltas if d <= 1.2]
between_1_2_and_2_0 = [d for d in deltas if 1.2 < d <= 2.0]
total_small = [d for d in deltas if d <= 2.0]

print(f"Total small gaps (<= 2.0s): {len(total_small)}")
print(f"  Gaps <= 1.2s:                 {len(below_1_2)} ({len(below_1_2)/len(total_small)*100:.1f}% of small, {len(below_1_2)/len(deltas)*100:.1f}% of total)")
print(f"  Gaps 1.2s - 2.0s:             {len(between_1_2_and_2_0)} ({len(between_1_2_and_2_0)/len(total_small)*100:.1f}% of small, {len(between_1_2_and_2_0)/len(deltas)*100:.1f}% of total)")

if between_1_2_and_2_0:
    print(f"Detail of gaps between 1.2s and 2.0s: {sorted(between_1_2_and_2_0)}")
