"""
FragEngine — Modular Multi-Game Base Interface (Base Game Module - BaseGM)
Provides abstract contracts for multi-game telemetry extraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseGameModule(ABC):
    """Abstract Base Class for Game Modules (GM)."""

    @property
    @abstractmethod
    def game_id(self) -> str:
        """Unique lower-case identifier for the game (e.g. 'sf', 'pubg', 'ff')."""
        pass

    @property
    @abstractmethod
    def game_title(self) -> str:
        """Human readable title of the game."""
        pass

    @property
    @abstractmethod
    def default_squad_size(self) -> int:
        """Default players per team/squad."""
        pass

    @property
    @abstractmethod
    def default_team_count(self) -> int:
        """Default total teams in a match."""
        pass

    @property
    @abstractmethod
    def default_ruleset(self) -> str:
        """Default tournament scoring ruleset ID (e.g. 'bmps')."""
        pass

    @abstractmethod
    def get_icon_paths(self) -> Dict[str, str]:
        """Returns map of weapon/event icon template paths."""
        pass

    @abstractmethod
    def get_dataset_paths(self) -> Dict[str, str]:
        """Returns dataset paths for team tag & player name auto-correction."""
        pass
