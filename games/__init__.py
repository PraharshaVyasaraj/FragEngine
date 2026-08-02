"""
FragEngine — Modular Multi-Game Registry (__init__.py)
Registry for dynamically loading and registering Game Modules (GMs).
"""

from typing import Dict
from games.base_game import BaseGameModule
from games.sf_gm import ScarFallGameModule, sf_gm

_GAME_MODULES: Dict[str, BaseGameModule] = {
    "sf": sf_gm,
    "scarfall": sf_gm
}


def get_game_module(game_id: str = "sf") -> BaseGameModule:
    """Returns the requested Game Module instance (default: 'sf')."""
    gid = game_id.lower().strip()
    if gid in _GAME_MODULES:
        return _GAME_MODULES[gid]
    raise ValueError(f"Game Module '{game_id}' is not registered. Available: {list(_GAME_MODULES.keys())}")


def register_game_module(game_module: BaseGameModule):
    """Registers a new Game Module into FragEngine."""
    _GAME_MODULES[game_module.game_id] = game_module
