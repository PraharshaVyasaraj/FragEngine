import csv
import datetime
import os

csv_path = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0008\v0.14_telemetry.csv'

if not os.path.exists(csv_path):
    print("CSV file not found!")
    exit(1)

rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

# Filter for rows where requests were actually processed by Flask
reqs = [r for r in rows if float(r['Total_Latency_ms']) > 0]

print(f"Total requests sent to Flask: {len(reqs)}")

# Parse timestamps
timestamps = [datetime.datetime.strptime(r['Timestamp'], "%Y-%m-%d %H:%M:%S.%f") for r in reqs]

# Calculate deltas between consecutive requests
deltas = []
for i in range(1, len(timestamps)):
    delta = (timestamps[i] - timestamps[i-1]).total_seconds()
    deltas.append(delta)

# Group requests into "Bursts" based on a gap threshold of e.g. 5 seconds
# If the gap between requests is < 5 seconds, they belong to the same burst.
burst_threshold = 5.0
bursts = []
current_burst = [timestamps[0]] if timestamps else []

for i in range(1, len(timestamps)):
    gap = (timestamps[i] - timestamps[i-1]).total_seconds()
    if gap <= burst_threshold:
        current_burst.append(timestamps[i])
    else:
        bursts.append(current_burst)
        current_burst = [timestamps[i]]
if current_burst:
    bursts.append(current_burst)

print(f"\n--- BURST TRAFFIC ANALYSIS (Gap Threshold = {burst_threshold}s) ---")
print(f"Number of distinct bursts detected: {len(bursts)}")

for idx, b in enumerate(bursts):
    start = b[0].strftime("%H:%M:%S")
    end = b[-1].strftime("%H:%M:%S")
    duration = (b[-1] - b[0]).total_seconds()
    print(f"Burst {idx:02d} | Start: {start} | End: {end} | Duration: {duration:.1f}s | Requests: {len(b)}")

# Let's count how many requests had gaps between 2.0s and 15.0s (the critical zone)
# If a gap is >2s but <15s, our 2-second cooldown would have returned to Normal mode, 
# but a 15-second lock would have kept us in Rapid mode.
critical_gaps = [d for d in deltas if 2.0 < d <= 15.0]
large_gaps = [d for d in deltas if d > 15.0]
small_gaps = [d for d in deltas if d <= 2.0]

print("\n--- DELTA DISTRIBUTION ANALYSIS ---")
print(f"Total gaps analyzed: {len(deltas)}")
print(f"  Gaps <= 2.0s (Handled by current cooldown):      {len(small_gaps)} ({len(small_gaps)/len(deltas)*100:.1f}%)")
print(f"  Gaps 2.0s - 15.0s (The 15s lock zone):          {len(critical_gaps)} ({len(critical_gaps)/len(deltas)*100:.1f}%)")
print(f"  Gaps > 15.0s (Clean idle gaps):                  {len(large_gaps)} ({len(large_gaps)/len(deltas)*100:.1f}%)")

if critical_gaps:
    print(f"  Detail of critical gaps (seconds): {sorted(critical_gaps)}")
