"""Shared configuration: tournament IDs, API bases and output paths.

To target a different tournament, change SEASON_ID (and COMPETITION_ID if needed).
2022 Qatar: COMPETITION_ID=17, SEASON_ID=255711
2026 (USA/Canada/Mexico): COMPETITION_ID=17, SEASON_ID=285023
"""

from pathlib import Path

COMPETITION_ID = "17"
SEASON_ID = "285023"
LANGUAGE = "en"

API_BASE = "https://api.fifa.com/api/v3"
FDH_BASE = "https://fdh-api.fifa.com/v1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# FIFA position codes used in squad data
POSITIONS = {0: "Goalkeeper", 1: "Defender", 2: "Midfielder", 3: "Striker"}
