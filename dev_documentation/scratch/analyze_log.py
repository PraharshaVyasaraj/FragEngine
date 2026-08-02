import re
from datetime import datetime
from collections import Counter

log_file = r'C:\Users\Praharsha\.gemini\antigravity-ide\brain\7deace2b-865e-41d1-898c-c4076727238a\.system_generated\tasks\task-1194.log'

with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Parse all POST timestamps
pattern = re.compile(r'\[13/Jul/2026 (\d{2}:\d{2}:\d{2})\] "POST /process')
times = []
for line in lines:
    m = pattern.search(line)
    if m:
        times.append(datetime.strptime('2026-07-13 ' + m.group(1), '%Y-%m-%d %H:%M:%S'))

print(f'Total POST /process requests: {len(times)}')
if times:
    print(f'First request : {times[0].strftime("%H:%M:%S")}')
    print(f'Last request  : {times[-1].strftime("%H:%M:%S")}')
    duration = (times[-1] - times[0]).total_seconds()
    print(f'Active session: {duration/60:.1f} minutes')

# Requests per minute
minute_counts = Counter(t.strftime('%H:%M') for t in times)
print('\nRequests per minute (top 10 busiest):')
for minute, count in sorted(minute_counts.items(), key=lambda x: -x[1])[:10]:
    print(f'  {minute} -> {count} requests')

# Find burst windows (>=10 requests in a single second)
second_counts = Counter(t.strftime('%H:%M:%S') for t in times)
bursts = [(t, c) for t, c in second_counts.items() if c >= 10]
bursts.sort()
print(f'\nBurst events (>=10 POSTs/second): {len(bursts)}')
for t, c in bursts[:15]:
    print(f'  {t} -> {c} requests')

# Find quiet gaps (>60 sec between requests)
gaps = []
for i in range(1, len(times)):
    diff = (times[i] - times[i-1]).total_seconds()
    if diff > 60:
        gaps.append((times[i-1].strftime('%H:%M:%S'), times[i].strftime('%H:%M:%S'), int(diff)))

print(f'\nQuiet gaps >60s (no requests):')
for g in gaps:
    print(f'  {g[0]} -> {g[1]} ({g[2]}s gap / {g[2]//60}min)')
