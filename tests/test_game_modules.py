"""
FragEngine Unit Tests — Game Modules (sf.gm)
"""

import pytest
from games import get_game_module
from games.sf_gm import ScarFallGameModule, sf_gm


def test_sf_game_module_properties():
    gm = get_game_module("sf")
    assert isinstance(gm, ScarFallGameModule)
    assert gm.game_id == "sf"
    assert gm.game_title == "ScarFall: The Royale Combat"
    assert gm.default_squad_size == 4
    assert gm.default_team_count == 12
    assert gm.default_ruleset == "bmps"


def test_sf_icon_paths():
    paths = sf_gm.get_icon_paths()
    assert "NADE" in paths
    assert "M416" in paths
    assert paths["NADE"].endswith("NADE.png")


def test_sf_dataset_paths():
    paths = sf_gm.get_dataset_paths()
    assert "team_tags" in paths
    assert "player_names" in paths
    assert "Team_Tags_Dataset_For_Training.csv" in paths["team_tags"]


def test_sf_default_roster():
    roster = sf_gm.get_default_scarfall_roster()
    assert len(roster) == 12
    assert roster[0]["tag"] == "PLTN"
