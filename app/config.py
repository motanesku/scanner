from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "scanner.db"
OUTPUT_PATH = OUTPUT_DIR / "latest_scan.json"
