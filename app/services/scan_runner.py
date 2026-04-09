# File: app/services/scan_runner.py

import json
from app.config import OUTPUT_PATH

from app.collectors.news_collector import collect_news_triggers
from app.collectors.sec_filings import collect_filings
from app.collectors.market_data import collect_market_data
from app.collectors.insider_collector import collect_insider_triggers
from app.collectors.earnings_collector import get_earnings_calendar

from app.parsers.news_parser import parse_news
from app.parsers.filing_parser import parse_filings

from app.engines.trigger_engine import classify_triggers
from app.engines.theme_mapper import map_triggers_to_opportunities
from app.engines.trigger_stack_builder import enrich_opportunities_with_trigger_stack

from app.scoring.catalyst_score import calculate_catalyst_score
from app.scoring.narrative_score import calculate_narrative_score
from app.scoring.market_score import calculate_market_score
from app.scoring.risk_score import calculate_risk_score

from app.utils.logger import log_info, log_success
from app.collectors.volume_history import save_volume_history
from app.collectors.volume_spike_collector import collect_volume_spike_triggers

# Universe încărcat o dată la startup
from app.engines.entity_resolver import get_universe
universe = get_universe()
log_info(f"[Scan] Universe: {universe.get('count', 0)} tickers, {universe.get('alias_count', 0)} aliases")


# ── Filtre de calitate ────────────────────────────────────────────────────────

def is_investable(opp: dict) -> bool:
    """
    Filtrează oportunitățile sub standardul minim de investabilitate.

    Filtru principal: daily turnover = price × volume >= $5M
    Acesta elimină micro-cap noise fără să atingă large/mid cap.

    Exemple:
    - APP $410 × 2.9M = $1.2B → KEEP
    - INSM $163 × 1.3M = $220M → KEEP
    - MVIS $0.59 × 4.9M = $2.9M → ELIMINATE
    - IKT $1.76 × 730K = $1.2M → ELIMINATE

    Dacă nu avem date Polygon (429) → păstrăm cu penalizare de scor.

    Volume spike standalone: păstrăm indiferent dacă au trigger real (spike IS trigger).
    """
    md = opp.get("market_data", {})
    price = md.get("price")
    volume = md.get("volume")
    status = md.get("status")
    trigger_stack = opp.get("trigger_stack", [])
    role = opp.get("role", "")

    # Volume spike e trigger real — nu îl filtrăm pe baza trigger_stack
    is_spike = "Volume Spike" in role

    if not is_spike:
        # Trigger pur theme fără nicio confirmare → eliminăm indiferent
        has_real_trigger = any(t != "Theme Trigger" for t in trigger_stack)
        if not has_real_trigger:
            return False

    # Fără date Polygon → păstrăm (scorul e deja penalizat cu -10)
    if status != "ok" or price is None or volume is None:
        return True

    # Penny stock hard filter
    if price < 2.0:
        return False

    # Daily turnover filter — elimină micro-cap fără să afecteze large/mid cap
    daily_turnover = price * volume
    if daily_turnover < 5_000_000:
        return False

    return True


def apply_quality_score_adjustments(opp: dict) -> dict:
    """
    Ajustează scorul în funcție de calitatea datelor disponibile.

    Nu elimină, doar penalizează:
    - Fără date Polygon → -10
    - Volum < 500K → -5
    - Preț < 5$ → -5
    """
    md = opp.get("market_data", {})
    price = md.get("price")
    volume = md.get("volume")
    status = md.get("status")

    score = opp["score"]

    if status != "ok":
        score -= 10  # nu știm lichiditatea

    elif price is not None and volume is not None:
        if price < 5.0:
            score -= 5
        if volume < 500_000:
            score -= 5

    opp["score"] = round(max(0, score), 1)
    return opp


def run_scan():
    log_info("Starting scan pipeline...")

    # ── 1. Triggere din știri (RSS) ───────────────────────────────────────────
    raw_news = collect_news_triggers()
    classified_triggers = classify_triggers(raw_news)
    log_info(f"[Scan] News triggers: {len(classified_triggers)}")

    # ── 2. Filing-uri SEC (8-K, etc.) ─────────────────────────────────────────
    filings = collect_filings()
    parsed_filings = parse_filings(filings)
    log_info(f"[Scan] SEC filings: {len(parsed_filings)}")

    # ── 2b. Insider triggers Form 4 ───────────────────────────────────────────
    insider_triggers = collect_insider_triggers(days_back=2)
    log_info(f"[Scan] Insider triggers (Form 4): {len(insider_triggers)}")

    # ── 2c. Earnings triggers 8-K ─────────────────────────────────────────────
    earnings_triggers = get_earnings_calendar()
    log_info(f"[Scan] Earnings triggers (8-K): {len(earnings_triggers)}")

    # ── 2d. Volume history → D1 + Volume spike triggers ───────────────────────
    # Salvăm volumele zilei și detectăm spikes ÎNAINTE de mapare
    # Astfel spike triggers ajung în map_triggers_to_opportunities (Tier 3)
    from app.collectors.market_data import preload_market_data, get_cached_grouped_data
    from datetime import datetime, timezone

    # Preload grouped daily — un singur request Polygon pentru toată piața
    n_preload = preload_market_data()
    log_info(f"[Scan] Market data preloaded early: {n_preload} tickers")

    grouped_data = get_cached_grouped_data()
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    if grouped_data:
        # Salvează în D1 (persistent cross-deploy)
        saved_ok = save_volume_history(grouped_data, today_str)
        log_info(f"[Scan] Volume history saved to D1: {saved_ok}")

        # Detectează spikes vs. media istorică din D1
        # tickers_to_check=None → broad scan pe toți tickerii cu turnover >= $5M
        volume_spike_triggers = collect_volume_spike_triggers(
            grouped_data,
            tickers_to_check=None,
        )
        log_info(f"[Scan] Volume spike triggers: {len(volume_spike_triggers)}")
        classified_triggers.extend(volume_spike_triggers)
    else:
        log_info("[Scan] No grouped data available — skipping volume spike detection")

    # ── 3. Oportunități mapate EXCLUSIV din triggere reale ────────────────────
    mapped_opportunities = map_triggers_to_opportunities(
        classified_triggers,
        insider_triggers=insider_triggers,
        earnings_triggers=earnings_triggers,
    )
    enriched_opportunities = enrich_opportunities_with_trigger_stack(
        mapped_opportunities,
        insider_triggers=insider_triggers
    )
    log_info(f"[Scan] Opportunities after enrichment: {len(enriched_opportunities)}")

    # ── 3b. SEC EDGAR SIC enrichment ──────────────────────────────────────────
    # Fetch SIC doar pentru tickerele din scan (~20-30 tickers)
    # Sursa: data.sec.gov/submissions — gratuit, oficial
    from app.collectors.sec_enricher import enrich_with_sic
    from app.engines.sic_theme_mapper import get_theme_for_ticker
    scan_tickers = [opp.ticker for opp in enriched_opportunities]
    sic_map = enrich_with_sic(scan_tickers)
    log_info(f"[Scan] SIC enriched: {len(sic_map)}/{len(scan_tickers)} tickers")

    # Aplică tema corectă din SIC pe fiecare oportunitate
    for opp in enriched_opportunities:
        sic_data = sic_map.get(opp.ticker)
        if not sic_data:
            continue
        sic_code, sic_desc = sic_data
        theme_result = get_theme_for_ticker(opp.ticker, sic_code)
        if theme_result is not None:
            opp.theme, opp.subtheme = theme_result
        elif sic_desc:
            # Sectorul nu e în mapare dar îl descriem corect
            opp.theme = sic_desc[:50]
            opp.subtheme = None

    # ── 4. Univers tickere ────────────────────────────────────────────────────
    tickers = list({opp.ticker for opp in enriched_opportunities})
    if not tickers:
        tickers = ["SPY"]

    # ── 5. Market data ────────────────────────────────────────────────────────
    # grouped_data deja preloaded la pasul 2d — collect_market_data folosește cache
    market_data = collect_market_data(tickers)

    # ── 6. Parsed news per ticker ─────────────────────────────────────────────
    parsed_news_input = []
    seen_news_per_ticker = set()

    for opp in enriched_opportunities:
        related_triggers = [
            trig for trig in classified_triggers
            if trig.theme_hint == opp.theme
        ]

        if not related_triggers:
            key = (opp.ticker, opp.theme, "fallback")
            if key not in seen_news_per_ticker:
                seen_news_per_ticker.add(key)
                parsed_news_input.append({
                    "ticker": opp.ticker,
                    "title": opp.theme,
                    "summary": opp.theme,
                    "source": "theme_fallback",
                    "link": ""
                })
            continue

        for trig in related_triggers:
            key = (opp.ticker, trig.headline)
            if key in seen_news_per_ticker:
                continue
            seen_news_per_ticker.add(key)
            parsed_news_input.append({
                "ticker": opp.ticker,
                "title": trig.headline,
                "summary": trig.headline,
                "source": "news_trigger",
                "link": ""
            })

    parsed_news = parse_news(parsed_news_input)

    # ── 7. Scoring final ──────────────────────────────────────────────────────
    final_opportunities = []

    for opp in enriched_opportunities:
        ticker = opp.ticker
        ticker_news = parsed_news.get(ticker, [])

        direct_triggers = 0
        theme_triggers = 0

        for item in ticker_news:
            title_upper = item.get("title", "").upper()
            company_upper = opp.company_name.upper()
            if ticker in title_upper or company_upper in title_upper:
                direct_triggers += 1
            else:
                theme_triggers = 1

        confirmation_triggers = 0

        for stack_item in opp.trigger_stack:
            if "Earnings" in stack_item:
                confirmation_triggers += 1

        md = market_data.get(ticker, {})
        if md.get("status") == "ok":
            if md.get("volume") and md.get("avg_volume_5d"):
                if md["avg_volume_5d"] > 0 and md["volume"] > md["avg_volume_5d"] * 1.5:
                    confirmation_triggers += 1
            if md.get("price") and md.get("previous_close"):
                if md["price"] > md["previous_close"]:
                    confirmation_triggers += 1

        has_insider_buy = any("Insider Buy" in s for s in opp.trigger_stack)
        if has_insider_buy:
            direct_triggers += 1

        # Volume spike contează ca direct trigger
        has_volume_spike = any("Volume Spike" in s for s in opp.trigger_stack)
        if has_volume_spike:
            direct_triggers += 1
            confirmation_triggers += 1

        catalyst_score = calculate_catalyst_score(
            ticker=ticker,
            parsed_filings=parsed_filings,
            parsed_news=parsed_news,
            market_data=market_data,
            insider_triggers=insider_triggers
        )
        narrative_score = calculate_narrative_score(
            ticker=ticker,
            parsed_news=parsed_news
        )
        market_score = calculate_market_score(
            ticker=ticker,
            market_data=market_data
        )
        risk_score = calculate_risk_score(
            ticker=ticker,
            parsed_filings=parsed_filings,
            parsed_news=parsed_news
        )

        final_score = round(
            (catalyst_score * 0.40) +
            (narrative_score * 0.25) +
            (market_score * 0.20) +
            ((100 - risk_score) * 0.15),
            1
        )

        signal_origin = "direct" if direct_triggers >= 1 else "theme"
        signal = determine_signal(
            score=final_score,
            risk_score=risk_score,
            direct_triggers=direct_triggers,
            confirmation_triggers=confirmation_triggers
        )

        why_now = build_why_now(
            signal_origin=signal_origin,
            ticker=ticker,
            company=opp.company_name,
            theme=opp.theme,
            has_insider=has_insider_buy,
            has_spike=has_volume_spike,
            trigger_stack=opp.trigger_stack,
        )

        insider_detail = next(
            (t for t in insider_triggers
             if t.get("ticker", "").upper() == ticker
             and t.get("transaction_type") == "P"),
            None
        )

        final_opportunities.append({
            "ticker": ticker,
            "company": opp.company_name,
            "theme": opp.theme,
            "subtheme": opp.subtheme,
            "role": opp.role,
            "positioning": opp.positioning,
            "market_cap_bucket": opp.market_cap_bucket,

            "signal_origin": signal_origin,
            "direct_triggers": direct_triggers,
            "theme_triggers": theme_triggers,
            "confirmation_triggers": confirmation_triggers,

            "score": final_score,
            "signal": signal,

            "catalyst_score": catalyst_score,
            "narrative_score": narrative_score,
            "market_score": market_score,
            "risk_score": risk_score,

            "why_now": why_now,
            "why_this_name": (
                f"{opp.company_name} este identificată ca {opp.role.lower()} "
                f"în tema {opp.theme}."
            ),
            "ai_verdict": "",

            "trigger_stack": opp.trigger_stack,
            "market_confirmation": opp.market_confirmation,
            "next_confirmations": opp.next_confirmations,
            "failure_modes": opp.failure_modes,

            "insider": {
                "name": insider_detail.get("insider_name", ""),
                "role": insider_detail.get("insider_role", ""),
                "value": insider_detail.get("total_value", 0),
                "date": insider_detail.get("transaction_date", ""),
                "filing_url": insider_detail.get("filing_url", ""),
            } if insider_detail else None,

            "entry": None,
            "target": None,
            "market_data": md
        })

    # ── 8. Ajustări calitate scor ─────────────────────────────────────────────
    final_opportunities = [apply_quality_score_adjustments(o) for o in final_opportunities]

    # ── 9. Filtru investabilitate ─────────────────────────────────────────────
    before_filter = len(final_opportunities)
    final_opportunities = [o for o in final_opportunities if is_investable(o)]
    log_info(f"[Scan] Quality filter: {before_filter} → {len(final_opportunities)} opportunities")

    # ── 10. Re-sortare după scor ajustat ──────────────────────────────────────
    final_opportunities = sorted(
        final_opportunities,
        key=lambda x: x["score"],
        reverse=True
    )

    # ── 11. Re-calculează signal după ajustări ────────────────────────────────
    for opp in final_opportunities:
        opp["signal"] = determine_signal(
            score=opp["score"],
            risk_score=opp["risk_score"],
            direct_triggers=opp["direct_triggers"],
            confirmation_triggers=opp["confirmation_triggers"]
        )

    # ── 12. Theme summary ─────────────────────────────────────────────────────
    themes = build_theme_summary(final_opportunities)

    # ── 13. Daily report ──────────────────────────────────────────────────────
    daily_report = build_daily_report(final_opportunities, themes)

    # ── 14. Output final ──────────────────────────────────────────────────────
    result = {
        "summary": {
            "total_opportunities": len(final_opportunities),
            "total_themes": len(themes),
            "insider_triggers_found": len(insider_triggers),
            "earnings_triggers_found": len(earnings_triggers),
            "scan_status": "ok"
        },
        "opportunities": final_opportunities,
        "themes": themes,
        "daily_report": daily_report
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    log_success(f"[Scan] Done — {len(final_opportunities)} investable opportunities.")
    return result


def determine_signal(score, risk_score, direct_triggers, confirmation_triggers):
    if direct_triggers >= 1 and confirmation_triggers >= 1 and score >= 75 and risk_score < 50:
        return "BUY"
    if direct_triggers >= 1:
        return "WATCH"
    if score >= 60:
        return "WATCH"
    return "PASS"


def build_why_now(
    signal_origin,
    ticker,
    company,
    theme,
    has_insider=False,
    has_spike=False,
    trigger_stack=None,
):
    """Generează contextul în română — folosit ca fallback dacă Haiku din Worker eșuează."""
    trigger_stack = trigger_stack or []

    # Spike fără alt catalizator — mesaj specific
    if has_spike and not has_insider:
        # Găsim ratio din trigger_stack dacă există
        spike_label = next((t for t in trigger_stack if "Volume Spike" in t), "Volume Spike")
        return (
            f"Activitate de volum neobișnuită detectată pentru {ticker} ({spike_label}) — "
            f"semnal de interes instituțional în tema {theme}."
        )

    if has_insider and signal_origin == "direct":
        return (
            f"Cumpărare insider detectată pentru {ticker} / {company}, "
            f"combinată cu narativa activă a temei {theme}."
        )

    if has_insider and has_spike:
        return (
            f"Cumpărare insider + volum neobișnuit pentru {ticker} — "
            f"convergență de semnale în tema {theme}."
        )

    if signal_origin == "direct":
        return f"Trigger direct specific companiei detectat pentru {ticker} / {company}."

    return (
        f"{theme} este activă în fluxul de știri curent, "
        f"iar {company} este identificată ca beneficiar relevant."
    )


def build_theme_summary(opportunities):
    theme_map = {}
    for opp in opportunities:
        theme = opp.get("theme", "General")
        if theme not in theme_map:
            theme_map[theme] = {"theme": theme, "strength_sum": 0, "count": 0, "tickers": []}
        theme_map[theme]["strength_sum"] += opp["score"]
        theme_map[theme]["count"] += 1
        theme_map[theme]["tickers"].append(opp["ticker"])

    result = []
    for theme, data in theme_map.items():
        avg = round(data["strength_sum"] / data["count"], 1) if data["count"] else 0
        result.append({
            "theme": theme,
            "strength": avg,
            "tickers": sorted(list(set(data["tickers"])))
        })
    return sorted(result, key=lambda x: x["strength"], reverse=True)


def build_daily_report(opportunities, themes):
    top_ideas = opportunities[:3]
    top_themes = themes[:3]
    return {
        "headline": (
            f"{top_themes[0]['theme']} este în prezent cea mai puternică narativă activă de piață."
            if top_themes else "Nicio narativă dominantă de piață detectată."
        ),
        "top_ideas": [
            {
                "ticker": x["ticker"],
                "score": x["score"],
                "signal": x["signal"],
                "theme": x["theme"],
                "why_now": x["why_now"],
            }
            for x in top_ideas
        ],
        "focus": [
            "Urmărește setup-uri de continuare cu triggere multiple",
            "Monitorizează filing-urile pentru risc de diluție sau finanțare",
            "Urmărește confirmarea volumului relativ și expansiunea tematică"
        ]
    }
