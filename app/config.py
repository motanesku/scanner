# File: app/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "scanner.db"
OUTPUT_PATH = OUTPUT_DIR / "latest_scan.json"

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
