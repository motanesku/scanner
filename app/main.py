from app.db import init_db
from app.services.scan_runner import run_scan
from app.services.export_service import export_to_json
from app.utils.logger import log_info, log_success


def main():
    log_info("Starting scanner MVP...")

    init_db()

    result = run_scan()
    export_to_json(result)

    log_success("Scanner run completed successfully.")