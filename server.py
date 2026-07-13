import torch
# Configure PyTorch CPU execution threads to balance speed (20-30ms) and latency
torch.set_num_threads(8)

import os
import re
import cv2
import numpy as np
import base64
import time
import difflib
from flask import Flask, request, jsonify
from flask_cors import CORS
from parser import FeedParser

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Paths
base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED"
icons_dir = r"E:\Games Data\SF FEED ICONS"
ql_path = os.path.join(base_dir, "QL.csv")

# Initialize Parser
parser = FeedParser(icons_dir)

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

print(f"[SERVER V0.12] Loaded {len(team_tags)} Team Tags and {len(player_names)} Player Names for auto-correction.")

# Initialize QL file
if not os.path.exists(ql_path):
    with open(ql_path, "w", encoding="utf-8") as f:
        f.write("Log # | Layout Type | T1 | I1 | I2 | T2\n")

# State Variables
last_log_entry = None  # Stores the normalized key tuple of the last logged event
log_counter = 1

# Time-based victim locks to prevent repeat logs: { (normalized_name, action): expiry_timestamp }
cooldown_locks = {}

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
    3. Split name by common separators (-, ~, _).
    4. Fuzzy match tag and name separately. Snaps if match confidence >= 85%, else leaves raw.
    """
    if not name:
        return ""

    # Clean leading digits (squad/team numbers)
    name = name.strip()
    name = re.sub(r"^\d+\s+", "", name)

    # Strip bracket noise like '[06]', '[O6]'
    name = re.sub(r"\[.*?\]", "", name)

    # Strip anything after a space (clan tags/status icons read as space-delimited text)
    name = name.split(" ")[0].strip()

    # Split by standard separators: - or ~ or _
    parts = re.split(r"([-~_])", name, maxsplit=1)
    
    if len(parts) >= 3:
        tag_part = parts[0]
        separator = parts[1]
        name_part = parts[2]
        
        # Soft match tag (tags are a smaller list, use 80% threshold)
        corrected_tag = correct_word_via_dict(tag_part, team_tags, threshold=0.80)
        # Soft match name (names are open-ended, use stricter 85% threshold)
        corrected_name = correct_word_via_dict(name_part, player_names, threshold=0.85)
        
        # Reconstruct normalized string preserving capitalization styling of the separator
        return f"{corrected_tag}{separator}{corrected_name}"
    else:
        # No separator: treat the whole string as a name and attempt a soft match
        return correct_word_via_dict(name, player_names, threshold=0.85)


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
    global last_log_entry, log_counter

    try:
        data = request.json
        if not data or "image" not in data:
            return jsonify({"status": "error", "message": "Missing image data"}), 400

        # Decode base64 JPEG frame
        image_data = data["image"]
        header, encoded = image_data.split(",", 1)
        decoded = base64.b64decode(encoded)
        np_arr = np.frombuffer(decoded, dtype=np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"status": "error", "message": "Failed to decode frame"}), 400

        # ─────────────────────────────────────────────────────────
        # V1.1 STAGE 1.5: BACKGROUND BRIGHTNESS SANITY CHECK
        # ─────────────────────────────────────────────────────────
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        if mean_brightness > EXPECTED_BG_MAX_BRIGHTNESS:
            print(f"[WALL BLOCKED] Bright frame (brightness={mean_brightness:.1f}) — likely UI noise, skipping OCR")
            return jsonify({"status": "skipped", "reason": f"Bright frame: {mean_brightness:.1f}"})

        # ─────────────────────────────────────────────────────────
        # V1.2 STAGE 2: OCR + TEMPLATE MATCH PIPELINE
        # ─────────────────────────────────────────────────────────

        # 3x Cubic Upscale for OCR legibility
        img_upscaled = cv2.resize(img, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

        # Run Parser
        res = parser.process_frame(img_upscaled)

        if res is None:
            return jsonify({"status": "skipped", "reason": "Unrecognizable layout"})

        # ─────────────────────────────────────────────────────────
        # V1.2 DATA CLEANING & AUTO-CORRECTION
        # ─────────────────────────────────────────────────────────
        res["t1"] = clean_and_normalize_name(res.get("t1", "") or "")
        res["t2"] = clean_and_normalize_name(res.get("t2", "") or "")

        # Minimum name length check (kills transient noise)
        if len(res["t1"]) < MIN_NAME_LENGTH:
            print(f"[WALL BLOCKED] T1 too short: '{res['t1']}'")
            return jsonify({"status": "skipped", "reason": f"T1 too short: {res['t1']}"})

        if res["layout"] == "2T2I" and len(res["t2"]) < MIN_NAME_LENGTH:
            print(f"[WALL BLOCKED] T2 too short: '{res['t2']}'")
            return jsonify({"status": "skipped", "reason": f"T2 too short: {res['t2']}"})

        # ─────────────────────────────────────────────────────────
        # V1.2 COOLDOWN CHECK: Keyed on (T2 + I2)
        # Prevents logging duplicate events for the same victim within 3.5 seconds
        # ─────────────────────────────────────────────────────────
        current_time = time.time()
        
        # Clean up expired locks from cooldown dictionary
        for locked_key, expiry in list(cooldown_locks.items()):
            if current_time >= expiry:
                cooldown_locks.pop(locked_key, None)
                
        # Check if current T2 is locked for the current action (I2)
        if res["layout"] == "2T2I" and res["t2"]:
            new_victim_name = res["t2"].upper()
            cooldown_blocked = False
            for locked_key, expiry in list(cooldown_locks.items()):
                locked_name, locked_icon = locked_key
                # Match same action (I2) and fuzzy-match the victim name
                if locked_icon == res["i2"]:
                    similarity = difflib.SequenceMatcher(None, new_victim_name, locked_name).ratio()
                    if similarity >= 0.82:
                        cooldown_blocked = True
                        break
            if cooldown_blocked:
                print(f"[WALL BLOCKED] Cooldown block on victim: '{res['t2']}' for action '{res['i2']}'")
                return jsonify({"status": "duplicate", "reason": f"Victim '{res['t2']}' in cooldown for '{res['i2']}'"})

        # ─────────────────────────────────────────────────────────
        # V1.2 FUZZY DEDUPLICATION
        # ─────────────────────────────────────────────────────────
        candidate_entry = (
            res["layout"],
            res["t1"],
            res["i1"],
            res["i2"],
            res["t2"] or ""
        )
        if last_log_entry and is_fuzzy_duplicate(candidate_entry, last_log_entry):
            print(f"[WALL BLOCKED] Fuzzy duplicate match: {res['t1']} -> {res['t2']}")
            return jsonify({"status": "duplicate"})

        # ─────────────────────────────────────────────────────────
        # APPROVED -> Save Lock, Update State, Write to CSV
        # ─────────────────────────────────────────────────────────
        if res["layout"] == "2T2I" and res["t2"]:
            # Register cooldown lock for this victim name + action
            cooldown_locks[(res["t2"].upper(), res["i2"])] = current_time + 3.5

        last_log_entry = candidate_entry
        log_line = f"Log {log_counter} | {res['layout']} | {res['t1']} | {res['i1']} | {res['i2']} | {res['t2']}\n"

        with open(ql_path, "a", encoding="utf-8") as f:
            f.write(log_line)

        print(f"[WALL PASSED] Logged: {log_line.strip()}")

        response_data = {
            "status": "logged",
            "log_num": log_counter,
            "data": res
        }
        log_counter += 1
        return jsonify(response_data)

    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print("Feed Parser V0.12 Server — High-Performance Active")
    app.run(host="127.0.0.1", port=5000, debug=False)
