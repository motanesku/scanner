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
            subtheme TEXT,
            role TEXT,
            positioning TEXT,
            market_cap_bucket TEXT,
            conviction_score REAL,
            priority_level TEXT,
            horizon TEXT,
            thesis TEXT,
            why_now TEXT,
            why_this_name TEXT,
            ai_verdict TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scanner_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_key TEXT,
            theme_name TEXT,
            theme_strength REAL,
            narrative_strength REAL,
            market_confirmation TEXT,
            priority_level TEXT,
            status TEXT,
            why_now TEXT,
            ai_verdict TEXT,
            top_beneficiaries TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scanner_daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT,
            top_themes TEXT,
            top_tickers TEXT,
            laggards TEXT,
            risk_flags TEXT,
            market_take TEXT,
            actionable_focus TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

    log_success("Database initialized.")


def save_run(run_type: str, summary: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO scanner_runs (run_type, summary)
            VALUES (:run_type, :summary)
            """),
            {"run_type": run_type, "summary": summary}
        )


def save_opportunities(opportunities: list):
    with engine.begin() as conn:
        for opp in opportunities:
            conn.execute(
                text("""
                INSERT INTO scanner_opportunities (
                    ticker, company_name, theme, subtheme, role, positioning,
                    market_cap_bucket, conviction_score, priority_level, horizon,
                    thesis, why_now, why_this_name, ai_verdict, status
                )
                VALUES (
                    :ticker, :company_name, :theme, :subtheme, :role, :positioning,
                    :market_cap_bucket, :conviction_score, :priority_level, :horizon,
                    :thesis, :why_now, :why_this_name, :ai_verdict, :status
                )
                """),
                opp.model_dump()
            )


def save_themes(themes: list):
    with engine.begin() as conn:
        for theme in themes:
            payload = theme.model_dump()
            payload["top_beneficiaries"] = ", ".join(payload["top_beneficiaries"])

            conn.execute(
                text("""
                INSERT INTO scanner_themes (
                    theme_key, theme_name, theme_strength, narrative_strength,
                    market_confirmation, priority_level, status, why_now,
                    ai_verdict, top_beneficiaries
                )
                VALUES (
                    :theme_key, :theme_name, :theme_strength, :narrative_strength,
                    :market_confirmation, :priority_level, :status, :why_now,
                    :ai_verdict, :top_beneficiaries
                )
                """),
                payload
            )


def save_daily_report(report):
    payload = report.model_dump()

    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO scanner_daily_reports (
                report_date, top_themes, top_tickers, laggards,
                risk_flags, market_take, actionable_focus
            )
            VALUES (
                :report_date, :top_themes, :top_tickers, :laggards,
                :risk_flags, :market_take, :actionable_focus
            )
            """),
            {
                "report_date": payload["report_date"],
                "top_themes": ", ".join(payload["top_themes"]),
                "top_tickers": ", ".join(payload["top_tickers"]),
                "laggards": ", ".join(payload["laggards"]),
                "risk_flags": ", ".join(payload["risk_flags"]),
                "market_take": payload["market_take"],
                "actionable_focus": ", ".join(payload["actionable_focus"]),
            }
        )
