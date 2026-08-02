import csv

csv_path = r'E:\Games Data\SAMPLE_IMAGESET_FEED\data\sessions\SESSION_0008\v0.14_telemetry.csv'

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader if float(r['Total_Latency_ms']) > 0]

print(f"Total processed requests: {len(rows)}")
for idx, r in enumerate(rows):
    print(f"Req {idx:02d} | Time: {r['Timestamp'].split(' ')[1]} | Total: {float(r['Total_Latency_ms']):.0f}ms | OCR: {float(r['OCR_ms']):.0f}ms | Conf: {float(r['OCR_Confidence_Avg']):.4f} | DictHits: {r['Dict_Hits']} | Sup: {r['Suppressed_Duplicates']}")
