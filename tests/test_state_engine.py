import time
import pytest
from utils.state_engine import StateEngine, PlayerState

@pytest.fixture
def sample_roster():
    return [
        {"tag": "KyZN", "name": "KyZN Esports", "players": ["EviLKiOz", "Shadow", "Viper", "Apex"]},
        {"tag": "FLCN", "name": "Falcon Squad", "players": ["PRADIP", "Hawk", "Falcon1", "Blaze"]}
    ]

def test_state_engine_initialization(sample_roster):
    engine = StateEngine(knock_timeout_seconds=30.0)
    engine.load_roster(sample_roster)

    snapshot = engine.get_snapshot()
    assert snapshot["teams_alive"] == 2
    assert "KYZN-EVILKIOZ" in snapshot["players"]
    assert snapshot["players"]["KYZN-EVILKIOZ"]["state"] == PlayerState.ALIVE

def test_knock_and_finish_flow(sample_roster):
    engine = StateEngine(knock_timeout_seconds=30.0)
    engine.load_roster(sample_roster)

    now = time.time()

    # 1. Knock Event
    res_knock = engine.process_event({
        "layout": "2T2I",
        "t1": "KyZN-EviLKiOz",
        "t2": "FLCN-PRADIP",
        "action": "KNOCK",
        "timestamp": now
    })

    assert res_knock["status"] == "processed"
    assert res_knock["victim_state"] == PlayerState.KNOCKED

    snapshot = engine.get_snapshot()
    assert snapshot["players"]["FLCN-PRADIP"]["state"] == PlayerState.KNOCKED

    # 2. Finish Event
    res_finish = engine.process_event({
        "layout": "2T2I",
        "t1": "KyZN-EviLKiOz",
        "t2": "FLCN-PRADIP",
        "action": "FINISH",
        "timestamp": now + 5.0
    })

    assert res_finish["status"] == "processed"
    assert res_finish["victim_state"] == PlayerState.ELIMINATED

def test_knock_30s_timeout_auto_revive(sample_roster):
    engine = StateEngine(knock_timeout_seconds=1.0) # Short 1s timeout for test
    engine.load_roster(sample_roster)

    start_time = time.time()

    engine.process_event({
        "layout": "2T2I",
        "t1": "KyZN-EviLKiOz",
        "t2": "FLCN-PRADIP",
        "action": "KNOCK",
        "timestamp": start_time
    })

    assert engine.players["FLCN-PRADIP"]["state"] == PlayerState.KNOCKED

    # Evaluate at start_time + 2s (exceeds 1s timeout)
    engine._evaluate_knock_timeouts(start_time + 2.0)
    assert engine.players["FLCN-PRADIP"]["state"] == PlayerState.ALIVE

def test_team_elimination_placement_rank(sample_roster):
    engine = StateEngine(knock_timeout_seconds=30.0)
    engine.load_roster(sample_roster)

    now = time.time()
    # Eliminate all 4 FLCN players
    for p_name in ["PRADIP", "Hawk", "Falcon1", "Blaze"]:
        engine.process_event({
            "layout": "2T2I",
            "t1": "KyZN-EviLKiOz",
            "t2": f"FLCN-{p_name}",
            "action": "FINISH",
            "timestamp": now
        })

    snapshot = engine.get_snapshot()
    assert snapshot["teams"]["FLCN"]["eliminated"] is True
    assert snapshot["teams"]["FLCN"]["placement_rank"] == 2 # 2nd place out of 2 teams (i.e. eliminated first)
    assert snapshot["teams_alive"] == 1
