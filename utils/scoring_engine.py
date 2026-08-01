import json
import os
import threading
from typing import Dict, List, Optional
from utils.state_engine import StateEngine

class ScoringEngine:
    """
    Decoupled Scoring Engine (FragEngine V0.16)
    Subscribes to StateEngine events and computes points according to an interchangeable JSON ruleset.
    """

    def __init__(self, state_engine: StateEngine, ruleset_path: Optional[str] = None):
        self.state_engine = state_engine
        self.lock = threading.Lock()

        # Default Ruleset Configurations
        self.ruleset_name: str = "Default Matrix"
        self.kill_point_value: float = 1.0
        self.allow_suicide_points: bool = False
        self.placement_point_table: Dict[int, int] = {
            1: 10, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 1
        }
        self.sort_priority: List[str] = ["total_points", "placement_points", "kill_points"]

        # Tracked Scores per Team: { "KyZN": { "kill_points": 2, "placement_points": 0, "total_points": 2, "finishes": 2 } }
        self.scores: Dict[str, dict] = {}

        # Subscribe to StateEngine Event Stream
        self.state_engine.register_event_callback(self.handle_state_event)

        if ruleset_path and os.path.exists(ruleset_path):
            self.load_ruleset(ruleset_path)

    def load_ruleset(self, ruleset_path: str):
        """Loads and applies a tournament scoring ruleset JSON configuration."""
        with self.lock:
            with open(ruleset_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.ruleset_name = config.get("ruleset_name", "Loaded Ruleset")
            self.kill_point_value = float(config.get("kill_point_value", 1.0))
            self.allow_suicide_points = bool(config.get("allow_suicide_points", False))
            
            raw_table = config.get("placement_point_table", {})
            self.placement_point_table = {int(k): int(v) for k, v in raw_table.items()}
            self.sort_priority = config.get("sort_priority", ["total_points", "placement_points", "kill_points"])

            print(f"[ScoringEngine] Applied ruleset: '{self.ruleset_name}' (Kill Val: {self.kill_point_value}).")
            self.recalculate_all()

    def handle_state_event(self, event_type: str, data: dict):
        """Event stream listener receiving events from StateEngine."""
        with self.lock:
            if event_type == "ON_KILL":
                killer_team = data.get("killer_team")
                is_enemy_kill = data.get("is_enemy_kill", False)

                if killer_team:
                    if killer_team not in self.scores:
                        self._init_team_score(killer_team)

                    if is_enemy_kill or self.allow_suicide_points:
                        self.scores[killer_team]["finishes"] += 1
                        self.scores[killer_team]["kill_points"] += self.kill_point_value
                        self.scores[killer_team]["total_points"] = (
                            self.scores[killer_team]["kill_points"] + self.scores[killer_team]["placement_points"]
                        )

            elif event_type == "ON_TEAM_ELIMINATED":
                team_tag = data.get("team_tag")
                placement_rank = data.get("placement_rank")

                if team_tag and placement_rank:
                    if team_tag not in self.scores:
                        self._init_team_score(team_tag)

                    # Placement Table Lookup
                    pp = self.placement_point_table.get(placement_rank, 0)
                    self.scores[team_tag]["placement_points"] = pp
                    self.scores[team_tag]["total_points"] = (
                        self.scores[team_tag]["kill_points"] + self.scores[team_tag]["placement_points"]
                    )

    def _init_team_score(self, team_tag: str):
        if team_tag not in self.scores:
            self.scores[team_tag] = {
                "finishes": 0,
                "kill_points": 0.0,
                "placement_points": 0,
                "total_points": 0.0
            }

    def recalculate_all(self):
        """Recalculates all team scores against current StateEngine snapshot and active ruleset."""
        snapshot = self.state_engine.get_snapshot()
        teams = snapshot.get("teams", {})

        for t_tag, t_info in teams.items():
            if t_tag not in self.scores:
                self._init_team_score(t_tag)

            p_rank = t_info.get("placement_rank")
            if p_rank and t_info.get("eliminated"):
                pp = self.placement_point_table.get(int(p_rank), 0)
                self.scores[t_tag]["placement_points"] = pp

            # Recalculate kill_points with active ruleset's kill_point_value
            self.scores[t_tag]["kill_points"] = self.scores[t_tag]["finishes"] * self.kill_point_value
            self.scores[t_tag]["total_points"] = (
                self.scores[t_tag]["kill_points"] + self.scores[t_tag]["placement_points"]
            )

    def get_leaderboard(self) -> List[dict]:
        """
        Returns real-time sorted leaderboard array driven by ruleset sort_priority.
        """
        with self.lock:
            snapshot = self.state_engine.get_snapshot()
            teams_info = snapshot.get("teams", {})

            leaderboard = []
            for t_tag, t_data in teams_info.items():
                sc = self.scores.get(t_tag, {"finishes": 0, "kill_points": 0.0, "placement_points": 0, "total_points": 0.0})
                leaderboard.append({
                    "team_tag": t_tag,
                    "team_name": t_data["name"],
                    "eliminated": t_data["eliminated"],
                    "placement_rank": t_data["placement_rank"],
                    "player_states": t_data["player_states"],
                    "finishes": sc["finishes"],
                    "kill_points": sc["kill_points"],
                    "placement_points": sc["placement_points"],
                    "total_points": sc["total_points"]
                })

            # Custom Sort Comparator driven by sort_priority
            def sort_key(item):
                keys = []
                for p in self.sort_priority:
                    if p == "total_points":
                        keys.append(item["total_points"])
                    elif p == "placement_points":
                        keys.append(item["placement_points"])
                    elif p == "kill_points":
                        keys.append(item["kill_points"])
                    elif p == "finishes":
                        keys.append(item["finishes"])
                # Also sort by inverse of placement_rank if eliminated
                p_rank = item["placement_rank"] if item["placement_rank"] else 999
                keys.append(-p_rank)
                return tuple(keys)

            leaderboard = sorted(leaderboard, key=sort_key, reverse=True)

            # Assign dynamic rank
            for i, entry in enumerate(leaderboard):
                entry["current_rank"] = i + 1

            return leaderboard
