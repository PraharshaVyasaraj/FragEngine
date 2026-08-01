"""
Unit test for AnalyticsEngine (Match Analytics & System Performance Benchmark Reporting)
"""

import os
import sys
import pytest

BASE_DIR = r"C:\FragEngine"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.analytics_engine import AnalyticsEngine
from utils.state_engine import StateEngine
from utils.scoring_engine import ScoringEngine

def test_analytics_engine_event_logging():
    engine = AnalyticsEngine("TEST_SESSION_001")
    engine.log_event({
        "type": "FINISH",
        "killer": "EviLKiOz",
        "killer_team": "KyZN",
        "victim": "CHAMP-08",
        "victim_team": "Tr",
        "weapon": "M416",
        "teams_alive": 12
    })
    
    assert len(engine.events_log) == 1
    assert engine.events_log[0]["killer"] == "EviLKiOz"
    assert engine.weapon_stats.get("M416") == 1

def test_analytics_engine_performance_export(tmp_path):
    state_engine = StateEngine()
    state_engine.load_roster([
        {"tag": "KyZN", "name": "KyZN Esports", "players": ["EviLKiOz", "Shadow", "Viper", "Apex"]}
    ])
    scoring_engine = ScoringEngine(state_engine, ruleset_path=os.path.join(BASE_DIR, "config", "rulesets", "bmps.json"))

    analytics = AnalyticsEngine("TEST_SESSION_002")
    analytics.log_performance_sample(capture_ms=1.4, ocr_ms=2.1, state_ms=0.2, total_ms=3.7, ocr_conf=0.98)
    analytics.log_event({
        "type": "FINISH",
        "killer": "EviLKiOz",
        "killer_team": "KyZN",
        "victim": "Target",
        "victim_team": "OPP",
        "weapon": "AK47",
        "teams_alive": 15
    })

    reports = analytics.export_match_analytics(state_engine, scoring_engine)

    assert os.path.exists(reports["json_report"])
    assert os.path.exists(reports["csv_report"])
    assert os.path.exists(reports["performance_report"])

    # Clean up test output files
    os.remove(reports["json_report"])
    os.remove(reports["csv_report"])
    os.remove(reports["performance_report"])
