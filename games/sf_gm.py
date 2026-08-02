"""
FragEngine — ScarFall Game Module (sf.gm)
Encapsulates 100% of ScarFall game-specific context, template icons,
default 12-16 team squad rules, and dataset auto-correction paths.
"""

import os
from typing import Dict, List, Any
from games.base_game import BaseGameModule

BASE_DIR = r"C:\FragEngine"


class ScarFallGameModule(BaseGameModule):
    """ScarFall Game Module (SF.GM) Implementation."""

    @property
    def game_id(self) -> str:
        return "sf"

    @property
    def game_title(self) -> str:
        return "ScarFall: The Royale Combat"

    @property
    def default_squad_size(self) -> int:
        return 4

    @property
    def default_team_count(self) -> int:
        return 12

    @property
    def default_ruleset(self) -> str:
        return "bmps"

    def get_icon_paths(self) -> Dict[str, str]:
        """Returns relative paths for ScarFall weapon and throwable icon templates."""
        icons_dir = os.path.join(BASE_DIR, "icons")
        return {
            "NADE": os.path.join(icons_dir, "THROWABLES", "NADE.png"),
            "M416": os.path.join(icons_dir, "WEAPONS", "M416.png"),
            "AKM": os.path.join(icons_dir, "WEAPONS", "AKM.png"),
            "AWM": os.path.join(icons_dir, "WEAPONS", "AWM.png"),
            "KNOCK": os.path.join(icons_dir, "STATES", "KNOCK.png"),
            "ELIM": os.path.join(icons_dir, "STATES", "ELIM.png")
        }

    def get_dataset_paths(self) -> Dict[str, str]:
        """Returns dataset paths for ScarFall team tag & player name auto-correction."""
        dataset_dir = os.path.join(BASE_DIR, "Dataset")
        return {
            "team_tags": os.path.join(dataset_dir, "TeamTags", "Team_Tags_Dataset_For_Training.csv"),
            "player_names": os.path.join(dataset_dir, "PlayerNames", "PlayerNames_Dataset_For_Training.csv")
        }

    def get_default_scarfall_roster(self) -> List[Dict[str, Any]]:
        """Returns pre-configured 12-team ScarFall tournament roster."""
        return [
            {"tag": "PLTN", "name": "Peloton", "players": ["P1", "P2", "P3", "P4"]},
            {"tag": "CPTN", "name": "Captains", "players": ["C1", "C2", "C3", "C4"]},
            {"tag": "SC", "name": "Shadow Clan", "players": ["S1", "S2", "S3", "S4"]},
            {"tag": "OCN", "name": "Ocean Esports", "players": ["O1", "O2", "O3", "O4"]},
            {"tag": "6SENSE", "name": "Sixth Sense", "players": ["61", "62", "63", "64"]},
            {"tag": "STAR", "name": "Star Alliance", "players": ["St1", "St2", "St3", "St4"]},
            {"tag": "RS", "name": "Rising Stars", "players": ["R1", "R2", "R3", "R4"]},
            {"tag": "XBUG", "name": "X-Bugs", "players": ["X1", "X2", "X3", "X4"]},
            {"tag": "KyZN", "name": "KyZN Esports", "players": ["EviLKiOz", "Shadow", "Viper", "Apex"]},
            {"tag": "FLCN", "name": "Falcon Squad", "players": ["PRADIP", "Hawk", "Falcon1", "Blaze"]},
            {"tag": "TxL", "name": "TxL Clan", "players": ["CLUSTER", "Striker", "Ghost", "Raven"]},
            {"tag": "Tr", "name": "Team Tr", "players": ["CHAMP-08", "Nitro", "Venom", "Storm"]}
        ]

# Create singleton instance alias sf_gm
sf_gm = ScarFallGameModule()
