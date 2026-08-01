import time
import pytest
from utils.state_engine import StateEngine
from utils.scoring_engine import ScoringEngine

@pytest.fixture
def sample_roster():
    return [
        {"tag": "KyZN", "name": "KyZN Esports", "players": ["EviLKiOz", "Shadow", "Viper", "Apex"]},
        {"tag": "FLCN", "name": "Falcon Squad", "players": ["PRADIP", "Hawk", "Falcon1", "Blaze"]}
    ]

def test_scoring_engine_bmps_matrix(sample_roster):
    state_engine = StateEngine()
    state_engine.load_roster(sample_roster)

    scoring_engine = ScoringEngine(state_engine, ruleset_path="config/rulesets/bmps.json")

    now = time.time()

    # KyZN gets 1 kill on FLCN-PRADIP
    state_engine.process_event({
        "layout": "2T2I",
        "t1": "KyZN-EviLKiOz",
        "t2": "FLCN-PRADIP",
        "action": "FINISH",
        "timestamp": now
    })

    leaderboard = scoring_engine.get_leaderboard()
    kyzn_score = next(item for item in leaderboard if item["team_tag"] == "KYZN")
    assert kyzn_score["finishes"] == 1
    assert kyzn_score["kill_points"] == 1.0
    assert kyzn_score["total_points"] == 1.0

def test_ruleset_switching_without_state_reset(sample_roster):
    state_engine = StateEngine()
    state_engine.load_roster(sample_roster)

    scoring_engine = ScoringEngine(state_engine, ruleset_path="config/rulesets/bmps.json")

    now = time.time()
    # Eliminate all 4 FLCN players
    for p_name in ["PRADIP", "Hawk", "Falcon1", "Blaze"]:
        state_engine.process_event({
            "layout": "2T2I",
            "t1": "KyZN-EviLKiOz",
            "t2": f"FLCN-{p_name}",
            "action": "FINISH",
            "timestamp": now
        })

    # Under BMPS: FLCN eliminated at Rank 2 -> PlacementTable[2] = 6 pts. KyZN has 4 kills = 4 pts.
    lb_bmps = scoring_engine.get_leaderboard()
    flcn_bmps = next(item for item in lb_bmps if item["team_tag"] == "FLCN")
    assert flcn_bmps["placement_points"] == 6

    # Switch Ruleset to Hardcore: PlacementTable[2] = 10 pts, Kills = 2.0 pts
    scoring_engine.load_ruleset("config/rulesets/hardcore.json")
    lb_hardcore = scoring_engine.get_leaderboard()
    
    flcn_hardcore = next(item for item in lb_hardcore if item["team_tag"] == "FLCN")
    kyzn_hardcore = next(item for item in lb_hardcore if item["team_tag"] == "KYZN")

    assert flcn_hardcore["placement_points"] == 10
    assert kyzn_hardcore["kill_points"] == 8.0 # 4 kills * 2.0
