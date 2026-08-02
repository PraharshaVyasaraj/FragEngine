import wmi
import time

c = wmi.WMI()
for i in range(3):
    t0 = time.perf_counter()
    # Direct raw WQL query targeting only the required field
    results = c.query("SELECT UtilizationPercentage FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine")
    utilizations = [int(r.UtilizationPercentage) for r in results if r.UtilizationPercentage]
    gpu_val = float(max(utilizations)) if utilizations else 0.0
    t1 = time.perf_counter()
    print(f"Query {i}: GPU={gpu_val}% (took {(t1-t0)*1000:.2f}ms)")
    time.sleep(0.5)
