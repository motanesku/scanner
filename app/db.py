from sqlalchemy import create_engine, text
from app.config import DB_PATH
from app.utils.logger import log_info, log_success

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


def init_db():
    log_info("Initializing local SQLite database...")

    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scanner_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_type TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scanner_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            company_name TEXT,
            theme TEXT,
            role TEXT,
            conviction_score REAL,
            priority_level TEXT,
            horizon TEXT,
            thesis TEXT,
            why_now TEXT,
            why_this_name TEXT,
            ai_verdict TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

    log_success("Database initialized.")