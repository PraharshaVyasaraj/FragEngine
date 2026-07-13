import os
import time
import json
import threading
import psutil
import datetime

class TelemetryCollector:
    def __init__(self, base_dir=r"E:\Games Data\SAMPLE_IMAGESET_FEED"):
        self.base_dir = base_dir
        self.session_dir = self._create_session_directory()
        
        # Telemetry Data Files
        self.csv_path = os.path.join(self.session_dir, "v0.13_telemetry.csv")
        self.json_path = os.path.join(self.session_dir, "v0.13_summary.json")
        
        # Initialize CSV Header
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("Timestamp,CPU_Percent,RAM_MB,Active_Threads,Voluntary_Ctx_Switches,Involuntary_Ctx_Switches,"
                    "Decode_ms,Preprocess_ms,OCR_ms,IconMatch_ms,DictCorrection_ms,Total_Latency_ms,"
                    "Dict_Hits,Suppressed_Duplicates\n")
            
        # State Tracking
        self.process = psutil.Process(os.getpid())
        self.is_running = False
        self.sampler_thread = None
        
        # Performance accumulator for summary
        self.latencies = {
            "decode": [], "preprocess": [], "ocr": [], 
            "icon_match": [], "dict_correction": [], "total": []
        }
        self.dict_hits = 0
        self.suppressed_duplicates = 0
        
        # Lock for thread-safe operations on accumulators
        self.lock = threading.Lock()

    def _create_session_directory(self):
        """Creates a unique SESSION_xxxx folder under data/sessions/"""
        sessions_parent = os.path.join(self.base_dir, "data", "sessions")
        os.makedirs(sessions_parent, exist_ok=True)
        
        existing = [d for d in os.listdir(sessions_parent) if d.startswith("SESSION_") and os.path.isdir(os.path.join(sessions_parent, d))]
        
        next_id = 1
        if existing:
            ids = []
            for name in existing:
                try:
                    ids.append(int(name.split("_")[1]))
                except ValueError:
                    pass
            if ids:
                next_id = max(ids) + 1
                
        session_name = f"SESSION_{next_id:04d}"
        session_path = os.path.join(sessions_parent, session_name)
        os.makedirs(session_path, exist_ok=True)
        print(f"[TELEMETRY] Initialized Match Session: {session_name}")
        return session_path

    def start(self):
        """Starts the background hardware metrics sampler"""
        if self.is_running:
            return
        self.is_running = True
        self.sampler_thread = threading.Thread(target=self._hardware_sampler_loop, daemon=True)
        self.sampler_thread.start()
        print("[TELEMETRY] Background hardware sampler thread started.")

    def stop(self):
        """Stops the background thread and exports summary stats"""
        if not self.is_running:
            return
        self.is_running = False
        if self.sampler_thread:
            self.sampler_thread.join(timeout=2.0)
        self._export_summary()
        print("[TELEMETRY] Background sampler stopped. Session metrics exported.")

    def _hardware_sampler_loop(self):
        """Samples hardware and process stats every 500ms and commits to telemetry CSV"""
        while self.is_running:
            try:
                # Sample CPU (system-wide and process-specific)
                cpu_sys = psutil.cpu_percent()
                mem_info = self.process.memory_info()
                ram_mb = mem_info.rss / (1024 * 1024)
                
                # Ctx switches and threads
                ctx_switches = self.process.num_ctx_switches()
                vol_ctx = ctx_switches.voluntary
                invol_ctx = ctx_switches.involuntary
                thread_count = self.process.num_threads()
                
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                with self.lock:
                    # Write hardware snapshot with 0ms placeholders for latency columns (which are logged per-request)
                    with open(self.csv_path, "a", encoding="utf-8") as f:
                        f.write(f"{timestamp},{cpu_sys:.1f},{ram_mb:.1f},{thread_count},{vol_ctx},{invol_ctx},"
                                f"0.0,0.0,0.0,0.0,0.0,0.0,0,0\n")
                                
            except Exception as e:
                print(f"[TELEMETRY ERROR] Error in hardware sampler loop: {e}")
                
            time.sleep(0.5)

    def log_request_performance(self, stages_ms, total_ms, dict_hits_count=0, duplicate_blocked=False):
        """Logs a single pipeline processing event with exact stage latency profiling"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        try:
            # Query current hardware metrics
            cpu_sys = psutil.cpu_percent()
            mem_info = self.process.memory_info()
            ram_mb = mem_info.rss / (1024 * 1024)
            ctx_switches = self.process.num_ctx_switches()
            vol_ctx = ctx_switches.voluntary
            invol_ctx = ctx_switches.involuntary
            thread_count = self.process.num_threads()
            
            # Extract stage timings
            dec = stages_ms.get("decode", 0.0)
            prep = stages_ms.get("preprocess", 0.0)
            ocr = stages_ms.get("ocr", 0.0)
            match = stages_ms.get("icon_match", 0.0)
            dict_corr = stages_ms.get("dict_correction", 0.0)
            
            # Update accumulators
            with self.lock:
                self.latencies["decode"].append(dec)
                self.latencies["preprocess"].append(prep)
                self.latencies["ocr"].append(ocr)
                self.latencies["icon_match"].append(match)
                self.latencies["dict_correction"].append(dict_corr)
                self.latencies["total"].append(total_ms)
                
                self.dict_hits += dict_hits_count
                if duplicate_blocked:
                    self.suppressed_duplicates += 1
                
                # Append request metrics to CSV
                with open(self.csv_path, "a", encoding="utf-8") as f:
                    f.write(f"{timestamp},{cpu_sys:.1f},{ram_mb:.1f},{thread_count},{vol_ctx},{invol_ctx},"
                            f"{dec:.2f},{prep:.2f},{ocr:.2f},{match:.2f},{dict_corr:.2f},{total_ms:.2f},"
                            f"{dict_hits_count},{1 if duplicate_blocked else 0}\n")
                            
        except Exception as e:
            print(f"[TELEMETRY ERROR] Error logging request performance: {e}")

    def _export_summary(self):
        """Compiles session-level statistics into summary.json"""
        with self.lock:
            total_requests = len(self.latencies["total"])
            
            def avg(lst):
                return sum(lst) / len(lst) if lst else 0.0
            
            summary = {
                "session_directory": self.session_dir,
                "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_events_processed": total_requests,
                "total_dictionary_corrections": self.dict_hits,
                "total_duplicates_blocked": self.suppressed_duplicates,
                "average_latencies_ms": {
                    "decode": avg(self.latencies["decode"]),
                    "preprocess": avg(self.latencies["preprocess"]),
                    "ocr": avg(self.latencies["ocr"]),
                    "icon_match": avg(self.latencies["icon_match"]),
                    "dict_correction": avg(self.latencies["dict_correction"]),
                    "total": avg(self.latencies["total"])
                },
                "max_latencies_ms": {
                    "decode": max(self.latencies["decode"]) if self.latencies["decode"] else 0.0,
                    "preprocess": max(self.latencies["preprocess"]) if self.latencies["preprocess"] else 0.0,
                    "ocr": max(self.latencies["ocr"]) if self.latencies["ocr"] else 0.0,
                    "icon_match": max(self.latencies["icon_match"]) if self.latencies["icon_match"] else 0.0,
                    "dict_correction": max(self.latencies["dict_correction"]) if self.latencies["dict_correction"] else 0.0,
                    "total": max(self.latencies["total"]) if self.latencies["total"] else 0.0
                }
            }
            
            try:
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=4)
            except Exception as e:
                print(f"[TELEMETRY ERROR] Error writing summary JSON: {e}")
