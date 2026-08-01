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
from flask import Flask, request, jsonify
from flask_cors import CORS
from parser import FeedParser

# Import V0.16 Decoupled Telemetry Engines
from utils.state_engine import StateEngine
from utils.scoring_engine import ScoringEngine

# Setup telemetry collector path
base_dir = r"C:\FragEngine"
from backend.telemetry import TelemetryCollector

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

# Paths
base_dir = r"C:\FragEngine"
icons_dir = r"C:\FragEngine\icons"
ql_path = os.path.join(base_dir, "QL.csv")

# Initialize Parser & V0.16 Match Engines
parser = FeedParser(icons_dir)
state_engine = StateEngine(knock_timeout_seconds=30.0)
ruleset_default_path = os.path.join(base_dir, "config", "rulesets", "bmps.json")
scoring_engine = ScoringEngine(state_engine, ruleset_path=ruleset_default_path)

# Load Dictionaries for Soft Auto-Correction
team_tags = []
tags_path = os.path.join(base_dir, "Dataset", "TeamTags", "Team_Tags_Dataset_For_Training.csv")
if os.path.exists(tags_path):
    try:
        with open(tags_path, "r", encoding="utf-8") as f:
            # Skip CSV header
            team_tags = [line.strip().upper() for line in f.readlines()[1:] if line.strip()]
    except Exception as e:
        print(f"Error loading TeamTags CSV: {e}")

player_names = []
players_path = os.path.join(base_dir, "Dataset", "PlayerNames", "PlayerNames_Dataset_For_Training.csv")
if os.path.exists(players_path):
    try:
        with open(players_path, "r", encoding="utf-8") as f:
            # Skip CSV header
            for line in f.readlines()[1:]:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    player_names.append(parts[1].strip().upper())
    except Exception as e:
        print(f"Error loading PlayerNames CSV: {e}")

print(f"[SERVER V0.15] Loaded {len(team_tags)} Team Tags and {len(player_names)} Player Names for auto-correction.")

# Initialize QL file
if not os.path.exists(ql_path):
    with open(ql_path, "w", encoding="utf-8") as f:
        f.write("Log # | Layout Type | T1 | I1 | I2 | T2\n")

# State Variables
import threading
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


# --- V1.2 CONFIGURATION CONSTANTS ---
MIN_NAME_LENGTH          = 3      # Minimum character length for OCR text blocks
MIN_ICON_CONFIDENCE      = 0.50   # Minimum template match score to accept an icon
EXPECTED_BG_MAX_BRIGHTNESS = 90   # Kill feed background is DARK. Skip if mean brightness > this threshold.


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
    V1.2 Soft Dictionary Auto-Corrector and Noise Stripper:
    1. Strip isolated trailing fragments like 'OV', 'ooy', or '[06]'.
    2. Strip anything after a space.
    3. Split name by common separators (-, ~, _, x).
    4. Fuzzy match tag and name separately. Snaps if match confidence >= 85%, else leaves raw.
    Returns (cleaned_name, corrections_count)
    """
    if not name:
        return "", 0

    corrections_count = 0
    # Clean leading digits (squad/team numbers)
    name = name.strip()
    name = re.sub(r"^\d+\s+", "", name)

    # Strip bracket noise like '[06]', '[O6]'
    name = re.sub(r"\[.*?\]", "", name)

    # Strip anything after a space (clan tags/status icons read as space-delimited text)
    name = name.split(" ")[0].strip()

    # Split by standard separators: - or ~ or _ or x
    parts = re.split(r"([-~_x])", name, maxsplit=1)
    
    if len(parts) >= 3:
        tag_part = parts[0]
        separator = parts[1]
        name_part = parts[2]
        
        # Soft match tag (tags are a smaller list, use 80% threshold)
        corrected_tag = correct_word_via_dict(tag_part, team_tags, threshold=0.80)
        if tag_part and corrected_tag != tag_part.upper():
            corrections_count += 1
            
        # Soft match name (names are open-ended, use stricter 85% threshold)
        corrected_name = correct_word_via_dict(name_part, player_names, threshold=0.85)
        if name_part and corrected_name != name_part.upper():
            corrections_count += 1
            
        # Reconstruct normalized string preserving capitalization styling of the separator
        return f"{corrected_tag}{separator}{corrected_name}", corrections_count
    else:
        # No separator: treat the whole string as a name and attempt a soft match
        corrected_name = correct_word_via_dict(name, player_names, threshold=0.85)
        if name and corrected_name != name.upper():
            corrections_count += 1
        return corrected_name, corrections_count


def is_fuzzy_duplicate(entry1, entry2):
    """
    V1.2 Fuzzy Deduplication:
    Compares two log entries (layout, t1, i1, i2, t2) to determine if they are duplicates.
    Requires layout and icons to match exactly, and T1/T2 strings to be >= 82% similar.
    """
    if not entry1 or not entry2:
        return False
    # entry format: (layout, t1, i1, i2, t2)
    if entry1[0] != entry2[0] or entry1[2] != entry2[2] or entry1[3] != entry2[3]:
        return False
    
    # Compare T1
    t1_similarity = difflib.SequenceMatcher(None, entry1[1].upper(), entry2[1].upper()).ratio()
    if t1_similarity < 0.82:
        return False
        
    # Compare T2 (if present)
    if entry1[4] or entry2[4]:
        if not entry1[4] or not entry2[4]:
            return False
        t2_similarity = difflib.SequenceMatcher(None, entry1[4].upper(), entry2[4].upper()).ratio()
        if t2_similarity < 0.82:
            return False
            
    return True


@app.route("/process", methods=["POST"])
def process_frame():
    global last_log_time, last_log_entry, log_counter

    telemetry.increment_request_count()
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
        data = request.json
        if not data or "image" not in data:
            return jsonify({"status": "error", "message": "Missing image data"}), 400

        # Decode base64 JPEG frame
        t_decode_start = time.perf_counter()
        image_data = data["image"]
        header, encoded = image_data.split(",", 1)
        decoded = base64.b64decode(encoded)
        np_arr = np.frombuffer(decoded, dtype=np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        stages_ms["decode"] = (time.perf_counter() - t_decode_start) * 1000

        if img is None:
            return jsonify({"status": "error", "message": "Failed to decode frame"}), 400

        # ─────────────────────────────────────────────────────────
        # V1.1 STAGE 1.5: BACKGROUND BRIGHTNESS SANITY CHECK
        # ─────────────────────────────────────────────────────────
        t_prep_start = time.perf_counter()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        if mean_brightness > EXPECTED_BG_MAX_BRIGHTNESS:
            stages_ms["preprocess"] = (time.perf_counter() - t_prep_start) * 1000
            total_ms = (time.perf_counter() - t_start) * 1000
            
            # Log skipped performance
            telemetry.log_request_performance(stages_ms, total_ms, duplicate_blocked=False, ocr_confidence=0.0, levenshtein_dist=0.0, status="skipped")
            print(f"[WALL BLOCKED] Bright frame (brightness={mean_brightness:.1f}) — likely UI noise, skipping OCR")
            return jsonify({"status": "skipped", "reason": f"Bright frame: {mean_brightness:.1f}"})

        # 3x Cubic Upscale for OCR legibility
        img_upscaled = cv2.resize(img, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        stages_ms["preprocess"] = (time.perf_counter() - t_prep_start) * 1000

        # ─────────────────────────────────────────────────────────
        # V1.2 STAGE 2: OCR + TEMPLATE MATCH PIPELINE
        # ─────────────────────────────────────────────────────────
        res = parser.process_frame(img_upscaled)

        if res is None or res.get("status") == "unrecognizable":
            if res and "_timings" in res:
                stages_ms["ocr"] = res["_timings"].get("ocr", 0.0)
            total_ms = (time.perf_counter() - t_start) * 1000
            telemetry.log_request_performance(stages_ms, total_ms, duplicate_blocked=False, ocr_confidence=0.0, levenshtein_dist=0.0, status="skipped")
            return jsonify({"status": "skipped", "reason": "Unrecognizable layout"})

        # Retrieve sub-stage timings and confidence from parser
        stages_ms["ocr"] = res.get("_timings", {}).get("ocr", 0.0)
        stages_ms["icon_match"] = res.get("_timings", {}).get("icon_match", 0.0)
        ocr_confidence = res.get("ocr_confidence", 0.0)

        # ─────────────────────────────────────────────────────────
        # V1.2 DATA CLEANING & AUTO-CORRECTION (with Server Lock)
        # ─────────────────────────────────────────────────────────
        with server_lock:
            t_dict_start = time.perf_counter()
            t1_orig = res.get("t1", "") or ""
            t2_orig = res.get("t2", "") or ""
            
            res["t1"], corrections_1 = clean_and_normalize_name(t1_orig)
            res["t2"], corrections_2 = clean_and_normalize_name(t2_orig)
            dict_hits_count = corrections_1 + corrections_2
            
            # Calculate Levenshtein edit distance
            import Levenshtein
            t1_edit = Levenshtein.distance(t1_orig.upper(), res["t1"].upper()) if corrections_1 > 0 else 0
            t2_edit = Levenshtein.distance(t2_orig.upper(), res["t2"].upper()) if corrections_2 > 0 else 0
            levenshtein_dist = float(t1_edit + t2_edit)
            
            stages_ms["dict_correction"] = (time.perf_counter() - t_dict_start) * 1000

            # Minimum name length check (kills transient noise)
            if len(res["t1"]) < MIN_NAME_LENGTH:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="skipped")
                print(f"[WALL BLOCKED] T1 too short: '{res['t1']}'")
                return jsonify({"status": "skipped", "reason": f"T1 too short: {res['t1']}"})

            if res["layout"] == "2T2I" and len(res["t2"]) < MIN_NAME_LENGTH:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="skipped")
                print(f"[WALL BLOCKED] T2 too short: '{res['t2']}'")
                return jsonify({"status": "skipped", "reason": f"T2 too short: {res['t2']}"})

            # ─────────────────────────────────────────────────────────
            # V0.14.3 RATE LIMITER: Enforce 400ms delta between logged events
            # ─────────────────────────────────────────────────────────
            current_time = time.time()
            if current_time - last_log_time < 0.400:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=True, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="duplicate")
                print(f"[WALL BLOCKED] Rate-limit threshold: <400ms since last log")
                return jsonify({"status": "duplicate", "reason": "Rate-limit threshold: <400ms since last log"})

            # ─────────────────────────────────────────────────────────
            # V0.14.3 DEDUPLICATION CHECK
            # ─────────────────────────────────────────────────────────
            candidate_entry = (
                res["layout"],
                res["t1"],
                res["i1"],
                res["i2"],
                res["t2"] or ""
            )
            
            is_duplicate = False
            duplicate_reason = ""

            if last_log_entry:
                # 1. Exact string matches are blocked
                if candidate_entry == last_log_entry:
                    is_duplicate = True
                    duplicate_reason = "Exact duplicate of last logged entry"
                # 2. Same layout & same outcome action check:
                #    If victim (T2) fuzzy-matches the previous victim name and it is within 5.0 seconds
                elif candidate_entry[0] == last_log_entry[0] and candidate_entry[3] == last_log_entry[3]:
                    # Verify both victim names are present
                    if candidate_entry[4] and last_log_entry[4]:
                        t2_similarity = difflib.SequenceMatcher(None, candidate_entry[4].upper(), last_log_entry[4].upper()).ratio()
                        if t2_similarity >= 0.82 and (current_time - last_log_time < 5.0):
                            is_duplicate = True
                            duplicate_reason = f"Fuzzy victim duplicate: '{candidate_entry[4]}' matches last log victim '{last_log_entry[4]}'"

            if is_duplicate:
                total_ms = (time.perf_counter() - t_start) * 1000
                telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=True, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="duplicate")
                print(f"[WALL BLOCKED] Duplicate: {duplicate_reason}")
                return jsonify({"status": "duplicate", "reason": duplicate_reason})

            # ─────────────────────────────────────────────────────────
            # APPROVED -> Update State, Write to CSV & Feed StateEngine
            # ─────────────────────────────────────────────────────────
            last_log_time = current_time
            last_log_entry = candidate_entry
            log_line = f"Log {log_counter} | {res['layout']} | {res['t1']} | {res['i1']} | {res['i2']} | {res['t2']}\n"

            with open(ql_path, "a", encoding="utf-8") as f:
                f.write(log_line)

            # Feed V0.16 Decoupled State Engine
            action_state = "FINISH"
            if res.get("i2") == "KNOCK":
                action_state = "KNOCK"
            elif res.get("i1") in ["ZONE", "FALL", "DROWN"]:
                action_state = f"{res.get('i1')}_FINISH"

            state_engine.process_event({
                "layout": res.get("layout"),
                "t1": res.get("t1"),
                "t2": res.get("t2"),
                "action": action_state,
                "timestamp": current_time
            })

            total_ms = (time.perf_counter() - t_start) * 1000
            telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="logged")
            print(f"[WALL PASSED] Logged: {log_line.strip()}")

            response_data = {
                "status": "logged",
                "log_num": log_counter,
                "data": res
            }
            log_counter += 1
            return jsonify(response_data)

    except Exception as e:
        total_ms = (time.perf_counter() - t_start) * 1000
        telemetry.log_request_performance(stages_ms, total_ms, dict_hits_count=dict_hits_count, duplicate_blocked=False, ocr_confidence=ocr_confidence, levenshtein_dist=levenshtein_dist, status="error")
        print(f"Error processing frame: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────
# V0.16 MATCH INTELLIGENCE API ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.route("/api/roster", methods=["POST"])
def load_match_roster():
    """Upload pre-match 16-team roster data."""
    try:
        data = request.json
        if not data or "teams" not in data:
            return jsonify({"status": "error", "message": "Missing 'teams' array in roster payload"}), 400

        teams_payload = data["teams"]
        state_engine.load_roster(teams_payload)
        scoring_engine.recalculate_all()
        return jsonify({"status": "success", "message": f"Loaded roster with {len(teams_payload)} teams."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/ruleset", methods=["POST"])
def select_scoring_ruleset():
    """Select active tournament scoring ruleset."""
    try:
        data = request.json
        if not data or "ruleset" not in data:
            return jsonify({"status": "error", "message": "Missing 'ruleset' name parameter"}), 400

        ruleset_name = data["ruleset"].lower().replace(".json", "")
        target_file = os.path.join(base_dir, "config", "rulesets", f"{ruleset_name}.json")

        if not os.path.exists(target_file):
            return jsonify({"status": "error", "message": f"Ruleset '{ruleset_name}' not found"}), 404

        scoring_engine.load_ruleset(target_file)
        return jsonify({"status": "success", "ruleset": scoring_engine.ruleset_name})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/telemetry_state", methods=["GET"])
def get_telemetry_state():
    """Returns live telemetry snapshot and real-time sorted leaderboard for HUD dashboard."""
    try:
        leaderboard = scoring_engine.get_leaderboard()
        snapshot = state_engine.get_snapshot()
        return jsonify({
            "status": "success",
            "active_ruleset": scoring_engine.ruleset_name,
            "teams_alive": snapshot["teams_alive"],
            "leaderboard": leaderboard
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print("FragEngine 0.16.0 — Active (Decoupled Telemetry Architecture)")
    app.run(host="127.0.0.1", port=5000, debug=False)
