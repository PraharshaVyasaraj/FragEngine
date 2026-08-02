"""
FragEngine V0.17 Unit Tests — AutoLearner Engine
"""

import pytest
import os
import tempfile
from utils.auto_learner import AutoLearner


@pytest.fixture
def auto_learner():
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = AutoLearner(base_dir=tmpdir)
        learner.team_tags_path = os.path.join(tmpdir, "TeamTags.csv")
        learner.player_names_path = os.path.join(tmpdir, "PlayerNames.csv")
        yield learner


def test_record_unrecognized_word(auto_learner):
    auto_learner.record_unrecognized_word("NV-SHADOW")
    candidates = auto_learner.get_candidates()

    tags = candidates["candidate_tags"]
    players = candidates["candidate_players"]

    assert any(t["name"] == "NV" for t in tags)
    assert any(p["name"] == "SHADOW" for p in players)


def test_approve_candidate(auto_learner):
    auto_learner.record_unrecognized_word("TESTTAG")
    res = auto_learner.approve_candidate("TESTTAG", "tag")

    assert res is True
    assert os.path.exists(auto_learner.team_tags_path)

    with open(auto_learner.team_tags_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "TESTTAG" in content


def test_ignore_candidate(auto_learner):
    auto_learner.record_unrecognized_word("TRASH")
    auto_learner.ignore_candidate("TRASH")

    candidates = auto_learner.get_candidates()
    assert not any(t["name"] == "TRASH" for t in candidates["candidate_tags"])
