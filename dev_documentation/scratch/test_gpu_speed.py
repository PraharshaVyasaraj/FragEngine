import wmi
import time

c = wmi.WMI()
for i in range(3):
    t0 = time.perf_counter()
    engines = c.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
    utilizations = [int(e.UtilizationPercentage) for e in engines if e.UtilizationPercentage]
    gpu_val = float(max(utilizations)) if utilizations else 0.0
    t1 = time.perf_counter()
    print(f"Sample {i}: GPU={gpu_val}% (query took {(t1-t0)*1000:.2f}ms)")
    time.sleep(0.5)
