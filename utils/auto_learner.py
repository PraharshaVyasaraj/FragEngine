"""
FragEngine V0.17 — Auto-Building Player & Team Tag Dictionary Engine
Tracks unrecognized OCR names, maintains candidate frequency buffers,
and persists approved tags to Dataset/TeamTags and Dataset/PlayerNames CSVs.
"""

import os
import re
import csv
import threading
from typing import Dict, List, Tuple

BASE_DIR = r"C:\FragEngine"
TEAM_TAGS_PATH = os.path.join(BASE_DIR, "Dataset", "TeamTags", "Team_Tags_Dataset_For_Training.csv")
PLAYER_NAMES_PATH = os.path.join(BASE_DIR, "Dataset", "PlayerNames", "PlayerNames_Dataset_For_Training.csv")


class AutoLearner:
    def __init__(self, base_dir: str = BASE_DIR):
        self.base_dir = base_dir
        self.team_tags_path = TEAM_TAGS_PATH
        self.player_names_path = PLAYER_NAMES_PATH
        self.lock = threading.Lock()

        # Candidate memory buffer: name -> frequency count
        self.candidate_tags: Dict[str, int] = {}
        self.candidate_players: Dict[str, int] = {}
        self.ignored_names: set = set()

    def record_unrecognized_word(self, raw_word: str):
        """Records an unrecognized OCR word and increments its occurrence candidate frequency."""
        if not raw_word or len(raw_word) < 3:
            return

        cleaned = raw_word.strip().upper()
        # Filter out numbers-only or trash symbols
        if cleaned.isdigit() or not re.search(r"[A-Z]", cleaned):
            return

        with self.lock:
            if cleaned in self.ignored_names:
                return

            # Determine if tag or player candidate based on length/structure
            if "-" in cleaned or "_" in cleaned or "~" in cleaned:
                parts = re.split(r"[-_~]", cleaned, maxsplit=1)
                tag_part = parts[0].strip()
                player_part = parts[1].strip() if len(parts) > 1 else ""

                if len(tag_part) >= 2:
                    self.candidate_tags[tag_part] = self.candidate_tags.get(tag_part, 0) + 1
                if len(player_part) >= 3:
                    self.candidate_players[player_part] = self.candidate_players.get(player_part, 0) + 1
            else:
                if len(cleaned) <= 5:
                    self.candidate_tags[cleaned] = self.candidate_tags.get(cleaned, 0) + 1
                else:
                    self.candidate_players[cleaned] = self.candidate_players.get(cleaned, 0) + 1

    def get_candidates(self) -> dict:
        """Returns candidate lists for team tags and player names sorted by frequency."""
        with self.lock:
            tags = [{"name": name, "count": count} for name, count in sorted(self.candidate_tags.items(), key=lambda x: x[1], reverse=True)]
            players = [{"name": name, "count": count} for name, count in sorted(self.candidate_players.items(), key=lambda x: x[1], reverse=True)]
            return {"candidate_tags": tags, "candidate_players": players}

    def approve_candidate(self, name: str, target_type: str) -> bool:
        """Approves a candidate tag/player, appending it to the CSV dataset file."""
        name_clean = name.strip().upper()
        if not name_clean:
            return False

        with self.lock:
            if target_type == "tag":
                if name_clean in self.candidate_tags:
                    del self.candidate_tags[name_clean]
                file_path = self.team_tags_path
            else:
                if name_clean in self.candidate_players:
                    del self.candidate_players[name_clean]
                file_path = self.player_names_path

            # Append to dataset CSV
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    if target_type == "tag":
                        writer.writerow([name_clean])
                    else:
                        writer.writerow(["", name_clean])
                print(f"[AUTO-LEARNER] Approved and appended '{name_clean}' to {target_type} dataset.")
                return True
            except Exception as e:
                print(f"[AUTO-LEARNER ERROR] Failed to save candidate: {e}")
                return False

    def ignore_candidate(self, name: str):
        """Ignores a candidate name so it is not prompted again."""
        name_clean = name.strip().upper()
        with self.lock:
            self.candidate_tags.pop(name_clean, None)
            self.candidate_players.pop(name_clean, None)
            self.ignored_names.add(name_clean)
