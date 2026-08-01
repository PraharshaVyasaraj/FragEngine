import time
import threading
from typing import Dict, List, Optional, Callable

class PlayerState:
    ALIVE = "ALIVE"
    KNOCKED = "KNOCKED"
    ELIMINATED = "ELIMINATED"

class StateEngine:
    """
    Immutable Match State Engine (FragEngine V0.16)
    Pure match mechanics only. Zero knowledge of points or scoring tables.
    """

    def __init__(self, knock_timeout_seconds: float = 30.0):
        self.knock_timeout_seconds = knock_timeout_seconds
        self.lock = threading.Lock()

        # { "TeamTag": { "name": "Team Name", "players": ["P1", "P2", "P3", "P4"] } }
        self.roster: Dict[str, dict] = {}

        # { "TeamTag-PlayerName": { "state": PlayerState.ALIVE, "team_tag": "TeamTag", "player_name": "P1", "knocked_at": timestamp } }
        self.players: Dict[str, dict] = {}

        # { "TeamTag": { "eliminated": False, "placement_rank": None } }
        self.teams: Dict[str, dict] = {}

        self.teams_alive_count: int = 0
        self.is_active: bool = False
        self.event_callbacks: List[Callable] = []

    def register_event_callback(self, callback: Callable):
        """Subscribe to StateEngine events (for ScoringEngine)."""
        self.event_callbacks.append(callback)

    def _emit_event(self, event_type: str, data: dict):
        for cb in self.event_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                print(f"[StateEngine Callback Error]: {e}")

    def load_roster(self, roster_data: List[dict]):
        """
        roster_data format:
        [
          { "tag": "KyZN", "name": "KyZN Esports", "players": ["EviLKiOz", "Shadow", "Viper", "Apex"] },
          ...
        ]
        """
        with self.lock:
            self.roster = {}
            self.players = {}
            self.teams = {}

            for t_info in roster_data:
                tag = t_info["tag"].strip().upper()
                name = t_info.get("name", tag)
                p_list = t_info.get("players", [])

                self.roster[tag] = {"name": name, "players": p_list}
                self.teams[tag] = {"eliminated": False, "placement_rank": None}

                for p_name in p_list:
                    p_clean = p_name.strip()
                    key = f"{tag}-{p_clean}".upper()
                    self.players[key] = {
                        "state": PlayerState.ALIVE,
                        "team_tag": tag,
                        "player_name": p_clean,
                        "knocked_at": None
                    }

            self.teams_alive_count = len(self.teams)
            self.is_active = True
            print(f"[StateEngine] Loaded roster: {len(self.teams)} teams, {len(self.players)} players.")

    def process_event(self, event_data: dict) -> dict:
        """
        Ingests parsed OCR event payload:
        {
          "layout": "2T2I" | "1T2I",
          "t1": "KyZN-EviLKiOz",
          "t2": "FLCN-PRADIP",
          "action": "KNOCK" | "FINISH" | "ZONE_FINISH",
          "timestamp": float
        }
        """
        with self.lock:
            if not self.is_active:
                return {"status": "ignored", "reason": "StateEngine not initialized with roster"}

            now = event_data.get("timestamp", time.time())
            action = event_data.get("action", "").upper()
            t1_str = event_data.get("t1", "")
            t2_str = event_data.get("t2", "")

            # 1. Clean background timeouts first
            self._evaluate_knock_timeouts(now)

            # Resolve Victim Key
            victim_key = self._resolve_player_key(t2_str)
            killer_key = self._resolve_player_key(t1_str) if t1_str else None

            if not victim_key or victim_key not in self.players:
                return {"status": "ignored", "reason": f"Victim player '{t2_str}' not found in registered roster"}

            victim = self.players[victim_key]
            v_team_tag = victim["team_tag"]

            is_enemy_kill = False
            if killer_key and killer_key in self.players:
                k_team_tag = self.players[killer_key]["team_tag"]
                if k_team_tag != v_team_tag:
                    is_enemy_kill = True

            # Process State Machine Transitions
            if "KNOCK" in action and "FINISH" not in action:
                if victim["state"] != PlayerState.ELIMINATED:
                    victim["state"] = PlayerState.KNOCKED
                    victim["knocked_at"] = now
                    self._emit_event("ON_KNOCK", {
                        "victim_key": victim_key,
                        "killer_key": killer_key,
                        "timestamp": now
                    })
            else:
                # FINISH or ZONE_FINISH or direct ELIMINATION
                if victim["state"] != PlayerState.ELIMINATED:
                    victim["state"] = PlayerState.ELIMINATED
                    victim["knocked_at"] = None

                    self._emit_event("ON_KILL", {
                        "victim_key": victim_key,
                        "killer_key": killer_key,
                        "victim_team": v_team_tag,
                        "killer_team": self.players[killer_key]["team_tag"] if (killer_key and killer_key in self.players) else None,
                        "is_enemy_kill": is_enemy_kill,
                        "timestamp": now
                    })

                    # Check if victim's team is completely eliminated
                    if self._check_team_eliminated(v_team_tag):
                        rank_assigned = self.teams_alive_count
                        self.teams[v_team_tag]["eliminated"] = True
                        self.teams[v_team_tag]["placement_rank"] = rank_assigned
                        self.teams_alive_count = max(1, self.teams_alive_count - 1)

                        self._emit_event("ON_TEAM_ELIMINATED", {
                            "team_tag": v_team_tag,
                            "placement_rank": rank_assigned,
                            "timestamp": now
                        })

            return {
                "status": "processed",
                "victim": victim_key,
                "victim_state": victim["state"],
                "teams_alive": self.teams_alive_count
            }

    def _evaluate_knock_timeouts(self, current_time: float):
        """Auto-reverts KNOCKED -> ALIVE after 30s if no finish occurs."""
        for p_key, p_data in self.players.items():
            if p_data["state"] == PlayerState.KNOCKED and p_data["knocked_at"]:
                if (current_time - p_data["knocked_at"]) >= self.knock_timeout_seconds:
                    p_data["state"] = PlayerState.ALIVE
                    p_data["knocked_at"] = None
                    self._emit_event("ON_KNOCK_TIMEOUT_REVIVE", {
                        "player_key": p_key,
                        "team_tag": p_data["team_tag"],
                        "timestamp": current_time
                    })

    def _check_team_eliminated(self, team_tag: str) -> bool:
        """Returns True if all registered players in team are ELIMINATED."""
        team_players = [p for p in self.players.values() if p["team_tag"] == team_tag]
        return all(p["state"] == PlayerState.ELIMINATED for p in team_players)

    def _resolve_player_key(self, name_str: str) -> Optional[str]:
        if not name_str:
            return None
        upper_str = name_str.strip().upper()
        if upper_str in self.players:
            return upper_str
        # Try finding key ending with name_str
        for key in self.players:
            if key.endswith(upper_str):
                return key
        return None

    def get_snapshot(self) -> dict:
        """Returns full immutable match state snapshot."""
        with self.lock:
            # Also evaluate timeouts on snapshot read
            self._evaluate_knock_timeouts(time.time())

            players_snapshot = {}
            for k, p in self.players.items():
                players_snapshot[k] = {
                    "team_tag": p["team_tag"],
                    "player_name": p["player_name"],
                    "state": p["state"]
                }

            teams_snapshot = {}
            for t_tag, t_data in self.teams.items():
                p_states = [self.players[f"{t_tag}-{p['player_name']}".upper()]["state"] 
                            for p in self.players.values() if p["team_tag"] == t_tag]
                teams_snapshot[t_tag] = {
                    "name": self.roster[t_tag]["name"],
                    "eliminated": t_data["eliminated"],
                    "placement_rank": t_data["placement_rank"],
                    "player_states": p_states
                }

            return {
                "teams_alive": self.teams_alive_count,
                "players": players_snapshot,
                "teams": teams_snapshot
            }
