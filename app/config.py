import os
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "dev")
DB_PATH = os.getenv("DB_PATH", "data/scanner.db")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "outputs/latest_scan.json")