# PyTorch thread settings removed in V0.15 for PaddleOCR + OpenVINO GPU transition

import os
import re
import cv2
import numpy as np
import base64
import time
import difflib
import sys
import signal
import atexit
import ctypes
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from flask_cors import CORS
from parser import FeedParser
from backend.telemetry import TelemetryCollector
from utils.loader import load_config, load_reference_datasets

# Load configuration centrally
config = load_config()
base_dir = config.get("base_dir", r"C:\FragEngine")
ql_path = config.get("ql_path", os.path.join(base_dir, "QL.csv"))

# Initialize Telemetry
telemetry = TelemetryCollector(base_dir)
telemetry.start()

def shutdown_handler(signum, frame):
    print("\n[SERVER] Shutdown signal received. Exporting telemetry logs...")
    telemetry.stop()
    sys.exit(0)

# Hook system signals for CTRL+C (SIGINT) and task cancellation (SIGTERM)
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Register atexit handler to guarantee summary export on any python exit
atexit.register(telemetry.stop)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Paths and parser initialization
icons_dir = config.get("icons_dir", os.path.join(base_dir, "icons"))
parser = FeedParser(icons_dir)

# Load Dictionaries for Soft Auto-Correction using modular loader
team_tags, player_names = load_reference_datasets(config)
print(f"[SERVER {config['version']}] Loaded {len(team_tags)} Team Tags and {len(player_names)} Player Names for auto-correction.")

# Initialize QL file
if not os.path.exists(ql_path):
    with open(ql_path, "w", encoding="utf-8") as f:
        f.write("Log # | Layout Type | T1 | I1 | I2 | T2\n")

# State Variables
server_lock = threading.Lock()
last_log_time = 0.0
last_log_entry = None  # Stores the normalized key tuple of the last logged event
log_counter = 1

# Load current log counter on startup
if os.path.exists(ql_path):
    try:
        with open(ql_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            valid_lines = [l for l in lines if l.startswith("Log")]
            log_counter = len(valid_lines) + 1
    except Exception:
        log_counter = 1

# --- CONFIGURATION CONSTANTS FROM JSON CONFIG ---
ocr_conf = config.get("ocr", {})
MIN_NAME_LENGTH = ocr_conf.get("min_name_length", 3)
MIN_ICON_CONFIDENCE = ocr_conf.get("min_icon_confidence", 0.50)
RATE_LIMIT_SEC = ocr_conf.get("rate_limit_sec", 0.400)
EXPECTED_BG_MAX_BRIGHTNESS = 90

# --- PRE-WARMED CORE AFFINITY SCHEDULER SETUP ---
def init_worker(worker_id_list, index_lock):
    """
    Called when each worker thread starts. Sets the Windows CPU affinity mask 
    to pin the thread to E-cores [12-19] of the i5-14500.
    """
    with index_lock:
        worker_id = worker_id_list.pop(0)
    try:
        kernel32 = ctypes.windll.kernel32
        thread_handle = kernel32.GetCurrentThread()
        # Pin worker to logical core 12 + worker_id (12-19)
        core_index = 12 + worker_id
        mask = 1 << core_index
        kernel32.SetThreadAffinityMask(thread_handle, mask)
        print(f"[BOOT] Standby worker thread {worker_id} bound to E-core {core_index}")
    except Exception as e:
        print(f"[BOOT WARNING] Failed to bind thread {worker_id} affinity: {e}")

worker_ids = list(range(8))
worker_index_lock = threading.Lock()
executor_pool = ThreadPoolExecutor(
    max_workers=8,
    initializer=init_worker,
    initargs=(worker_ids, worker_index_lock)
)


def correct_word_via_dict(word, dictionary, threshold=0.85):
    """Fuzzy match word against dictionary. Snaps to closest match if similarity >= threshold."""
    if not word:
        return ""
    word_upper = word.upper()
    matches = difflib.get_close_matches(word_upper, dictionary, n=1, cutoff=threshold)
    if matches:
        return matches[0]
    return word_upper

def clean_and_normalize_name(name):
    """
    Soft Dictionary Auto-Corrector and Noise Stripper:
    1. Strip isolated trailing fragments.
    2. Strip anything after a space.
    3. Split name by common separators (-, ~, _, x).
    4. Fuzzy match tag and name separately.
    """
    if not name:
        return "", 0

    corrections_count = 0
    name = name.strip()
    name = re.sub(r"^\d+\s+", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    name = name.split(" ")[0].strip()
    parts = re.split(r"([-~_x])", name, maxsplit=1)
    
    if len(parts) >= 3:
        tag_part = parts[0]
        separator = parts[1]
        name_part = parts[2]
        
        corrected_tag = correct_word_via_dict(tag_part, team_tags, threshold=0.80)
        if tag_part and corrected_tag != tag_part.upper():
            corrections_count += 1
            
        corrected_name = correct_word_via_dict(name_part, player_names, threshold=0.85)
        if name_part and corrected_name != name_part.upper():
            corrections_count += 1
            
        return f"{corrected_tag}{separator}{corrected_name}", corrections_count
    else:
        corrected_name = correct_word_via_dict(name, player_names, threshold=0.85)
        if name and corrected_name != name.upper():
            corrections_count += 1
        return corrected_name, corrections_count

def is_fuzzy_duplicate(entry1, entry2):
    """
    Fuzzy Deduplication:
    Compares two log entries (layout, t1, i1, i2, t2) to determine if they are duplicates.
    Requires layout and icons to match exactly, and T1/T2 strings to be >= 82% similar.
    """
    if not entry1 or not entry2:
        return False
    if entry1[0] != entry2[0] or entry1[2] != entry2[2] or entry1[3] != entry2[3]:
        return False
    
    t1_similarity = difflib.SequenceMatcher(None, entry1[1].upper(), entry2[1].upper()).ratio()
    if t1_similarity < 0.82:
        return False
        
    if entry1[4] or entry2[4]:
        if not entry1[4] or not entry2[4]:
            return False
        t2_similarity = difflib.SequenceMatcher(None, entry1[4].upper(), entry2[4].upper()).ratio()
        if t2_similarity < 0.82:
            return False
            
    return True


def decode_base64_img(base64_str):
    if not base64_str:
        return None
    try:
        header, encoded = base64_str.split(",", 1)
        decoded = base64.b64decode(encoded)
        np_arr = np.frombuffer(decoded, dtype=np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def process_frame_task(t1_image, t2_image, icon_image, row_index):
    """
    Executes the frame parsing, OCR, and validation stages on a standby worker thread.
    """
    global last_log_time, last_log_entry, log_counter
    
    t_start = time.perf_counter()
    stages_ms = {
        "decode": 0.0,
        "preprocess": 0.0,
        "ocr": 0.0,
        "icon_match": 0.0,
        "dict_correction": 0.0
    }
    dict_hits_count = 0
    ocr_confidence = 0.0
    levenshtein_dist = 0.0

    try:
        # Decode base64 JPEG crops
        t_decode_start = time.perf_counter()
        img_icon = decode_base64_img(icon_image)
        img_t1 = decode_base64_img(t1_image)
        img_t2 = decode_base64_img(t2_image)
        stages_ms["decode"] = (time.perf_counter() - t_decode_start) * 1000

        if img_icon is None:
            return {"status": "error", "message": "Failed to decode icon crop"}, 400

        t_prep_start = time.perf_counter()
        gray_icon = cv2.cvtColor(img_icon, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray_icon))
        if mean_brightness > EXPECTED_BG_MAX_BRIGHTNESS:
            stages_ms["preprocess"] = (time.perf_counter() - t_prep_start) * 1000
            total_ms = (time.perf_counter() - t_start) * 1000
            
            telemetry.log_request_performance(stages_ms, total_ms, duplicate_blocked=False, ocr_confidence=0.0, levenshtein_dist=0.0, status="skipped", row_index=row_index)
            print(f"[WALL BLOCKED] Row {row_index} bright (brightness={mean_brightness:.1f}) — skipping parsing")
            return {"status": "skipped", "reason": f"Bright frame: {mean_brightness:.1f}"}, 200

        stages_ms["preprocess"] = (time.perf_counter() - t_prep_start) * 1000

        # OCR + TEMPLATE MATCH PIPELINE
        res = parser.process_3rois(img_t1, img_t2, img_icon)

        if res is None or res.get("status") == "unrecognizable":
            if res and "_timings" in res:
                stages_ms["ocr"] = res["_timings"].get("ocr", 0.0)
            total_ms = (time.perf_counter() - t_start) * 1000
            telemetry.log_request_performance(stages_ms, total_ms, duplicate_blocked=False, ocr_confidence=0.0, levenshtein_dist=0.0, status="skipped", row_index=row_index)
            return {"status": "skipped", "reason": "Unrecognizable layout"}, 200

        # Retrieve timings and confidence from parser
        stages_ms["ocr"] = res["_timings"].get("ocr", 0.0)
        stages_ms["icon_match"] = res["_timings"].get("icon_match", 0.0)
        ocr_confidence = res.get("ocr_confidence", 0.0)

        # Event level data quality check
        res["Row_Index"] = row_index
        telemetry.validator.validate_parsed_event(res)

        # STAGE 3: SOFT DICTIONARY AUTO-CORRECTION
        t_dict_start = time.perf_counter()
        t1_raw = res["t1"]
        t2_raw = res["t2"]

        t1_clean, t1_corr = clean_and_normalize_name(t1_raw)
        t2_clean, t2_corr = clean_and_normalize_name(t2_raw)

        res["t1"] = t1_clean
        res["t2"] = t2_clean

        dict_hits_count = t1_corr + t2_corr
        stages_ms["dict_correction"] = (time.perf_counter() - t_dict_start) * 1000

        # Calculate Levenshtein distance if correction occurred
        if dict_hits_count > 0:
            l1 = difflib.SequenceMatcher(None, t1_raw.upper(), t1_clean.upper()).distance() if hasattr(difflib.SequenceMatcher, 'distance') else 1.0
            l2 = difflib.SequenceMatcher(None, t2_raw.upper(), t2_clean.upper()).distance() if hasattr(difflib.SequenceMatcher, 'distance') else 1.0
            levenshtein_dist = float(l1 + l2) / dict_hits_count

        # STAGE 4: CONCURRENCY & DEDUPLICATION GATES
        with server_lock:
            if res["layout"] == "T2I2":
                if len(res["t1"]) < MIN_NAME_LENGTH or len(res["t2"]) < MIN_NAME_LENGTH:
                    total_ms = (time.perf_counter() - t_start) * 1000
                    telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="skipped", row_index=row_index)
                    print(f"[WALL BLOCKED] T1 or T2 too short: '{res['t1']}' / '{res['t2']}'")
                    return {"status": "skipped", "reason": f"T1 or T2 too short: {res['t1']} / {res['t2']}"}, 200
            elif res["layout"] == "T1I2":
                if len(res["t1"]) < MIN_NAME_LENGTH:
                    total_ms = (time.perf_counter() - t_start) * 1000
                    telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="skipped", row_index=row_index)
                    print(f"[WALL BLOCKED] T1 too short: '{res['t1']}'")
                    return {"status": "skipped", "reason": f"T1 too short: {res['t1']}"}, 200

            # Temporal Rate-Limit Gate (400ms threshold)
            current_time = time.time()
            if current_time - last_log_time < RATE_LIMIT_SEC:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=True, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="duplicate", row_index=row_index)
                print(f"[WALL BLOCKED] Rate-limit threshold: <{RATE_LIMIT_SEC * 1000:.0f}ms since last log")
                return {"status": "duplicate", "reason": f"Rate-limit threshold: <{RATE_LIMIT_SEC * 1000:.0f}ms since last log"}, 200

            # Spatial-Similarity Deduplication Gate (82% Levenshtein/Fuzzy match)
            candidate_entry = (res["layout"], res["t1"], res["i1"], res["i2"], res["t2"])
            is_duplicate = False
            duplicate_reason = ""
            
            if last_log_entry is not None:
                if is_fuzzy_duplicate(candidate_entry, last_log_entry):
                    is_duplicate = True
                    duplicate_reason = f"Duplicate event structure: {candidate_entry} matching previous log"

            if is_duplicate:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=True, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="duplicate", row_index=row_index)
                print(f"[WALL BLOCKED] Duplicate: {duplicate_reason}")
                return {"status": "duplicate", "reason": duplicate_reason}, 200

            # APPROVED -> Update State, Write to CSV
            last_log_time = current_time
            last_log_entry = candidate_entry
            log_line = f"Log {log_counter} | {res['layout']} | {res['t1']} | {res['i1']} | {res['i2']} | {res['t2']}\n"

            with open(ql_path, "a", encoding="utf-8") as f:
                f.write(log_line)

            total_ms = (time.perf_counter() - t_start) * 1000
            telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="logged", row_index=row_index)
            print(f"[WALL PASSED] Logged (Row {row_index}): {log_line.strip()}")

            response_data = {
                "status": "logged",
                "log_num": log_counter,
                "data": res
            }
            log_counter += 1
            return response_data, 200

    except Exception as e:
        total_ms = (time.perf_counter() - t_start) * 1000
        telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="error", row_index=row_index)
        print(f"Error processing frame segment: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route("/process", methods=["POST"])
def process_frame():
    telemetry.increment_request_count()
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Missing request body"}), 400

        t1_image = data.get("t1_image")
        t2_image = data.get("t2_image")
        icon_image = data.get("icon_image")
        row_index = int(data.get("row_index", 0))

        if not icon_image:
            return jsonify({"status": "error", "message": "Missing icon image crop"}), 400

        # Submit task to the pre-warmed affinity-bound thread pool
        future = executor_pool.submit(process_frame_task, t1_image, t2_image, icon_image, row_index)
        res_data, status_code = future.result()
        return jsonify(res_data), status_code
    except Exception as e:
        print(f"Server routing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print(f"FragEngine {config['version']} — Active (FragLab Analytics)")
    app.run(host=config["server"]["host"], port=config["server"]["port"], debug=config["server"]["debug"], threaded=True)
