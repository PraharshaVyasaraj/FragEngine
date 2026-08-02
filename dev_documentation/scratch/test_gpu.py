try:
    import win32com.client
    wmi = win32com.client.GetObject("winmgmts:")
    for obj in wmi.InstancesOf("Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine"):
        print(obj.Name, obj.UtilizationPercentage)
except Exception as e:
    print("Error:", e)
