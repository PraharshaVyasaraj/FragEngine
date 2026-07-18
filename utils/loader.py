import os
import json
import csv

def load_config():
    """Loads settings from config/config.json."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config.json from {config_path}: {e}")
        # Return fallback configuration
        return {
            "version": "0.16.0",
            "base_dir": r"C:\FragEngine",
            "icons_dir": r"C:\FragEngine\icons",
            "ql_path": r"C:\FragEngine\QL.csv",
            "datasets": {
                "team_tags_path": r"C:\FragEngine\Dataset\TeamTags\Team_Tags_Dataset_For_Training.csv",
                "player_names_path": r"C:\FragEngine\Dataset\PlayerNames\PlayerNames_Dataset_For_Training.csv"
            },
            "ocr": {
                "min_name_length": 3,
                "min_icon_confidence": 0.50,
                "rate_limit_sec": 0.400
            },
            "server": {
                "host": "127.0.0.1",
                "port": 5000,
                "debug": false
            }
        }

def load_reference_datasets(config):
    """
    Loads team tags and player names reference data according to DMBOK Reference and Master Data principles.
    Returns: (team_tags_list, player_names_list)
    """
    team_tags = []
    player_names = []
    
    tags_path = config["datasets"]["team_tags_path"]
    players_path = config["datasets"]["player_names_path"]
    
    # Load Team Tags
    if os.path.exists(tags_path):
        try:
            with open(tags_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header
                for row in reader:
                    if row and row[0].strip():
                        team_tags.append(row[0].strip().upper())
            # Deduplicate while preserving order
            team_tags = list(dict.fromkeys(team_tags))
        except Exception as e:
            print(f"[ERROR] Loading TeamTags failed: {e}")
            
    # Load Player Names
    if os.path.exists(players_path):
        try:
            with open(players_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 2 and row[1].strip():
                        player_names.append(row[1].strip().upper())
            # Deduplicate while preserving order
            player_names = list(dict.fromkeys(player_names))
        except Exception as e:
            print(f"[ERROR] Loading PlayerNames failed: {e}")
            
    return team_tags, player_names
