# File: app/services/haiku_enricher.py
#
# Generează ai_verdict și why_now personalizat via Claude Haiku.
# Folosește requests + ThreadPoolExecutor (fără aiohttp).
# Rulează paralel pentru toate oportunitățile din scan.

import os
import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.logger import log_info, log_warn, log_error

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"
MAX_WORKERS = 5  # requests paralele

SYSTEM_PROMPT = """Ești un analist de investiții senior care scrie analize concise în limba română.
Stilul tău: direct, factual, fără exagerări. Maxim 2-3 propoziții per câmp.
Nu folosi bullet points. Nu repeta datele din input verbatim — interpretează-le."""


def _build_prompt(opp: dict) -> str:
    md = opp.get("market_data", {})
    price = md.get("price")
    volume = md.get("volume")
    vwap = md.get("vwap")

    trigger_stack = opp.get("trigger_stack", [])
    triggers_str = " + ".join(trigger_stack)

    volume_context = ""
    if price and volume:
        turnover = price * volume / 1_000_000
        volume_context = f"Turnover zilnic: ${turnover:.1f}M."
    if vwap and price:
        diff_pct = ((price - vwap) / vwap) * 100
        direction = "peste" if diff_pct > 0 else "sub"
        volume_context += f" Close {direction} VWAP cu {abs(diff_pct):.1f}%."

    return f"""Analizează această oportunitate și generează în română:
1. "ai_verdict": teză de investiție în 2-3 propoziții (de ce e sau nu e interesant acum)
2. "why_now": context specific în 1-2 propoziții (ce se întâmplă concret acum)

Date:
- Ticker: {opp.get('ticker')} — {opp.get('company')}
- Temă: {opp.get('theme')} / {opp.get('subtheme', 'N/A')}
- Rol: {opp.get('role')} | Semnal: {opp.get('signal')} | Scor: {opp.get('score')}
- Trigger stack: {triggers_str}
- Catalyst: {opp.get('catalyst_score')} | Narrative: {opp.get('narrative_score')} | Risk: {opp.get('risk_score')}
- Preț: ${price} | Volum: {f"{volume:,}" if volume else "N/A"} shares
- {volume_context}

Răspunde STRICT în format JSON fără text extra:
{{"ai_verdict": "...", "why_now": "..."}}"""


def _enrich_single(opp: dict) -> dict:
    """Enrichează o singură oportunitate cu Haiku."""
    ticker = opp.get("ticker", "")

    if not ANTHROPIC_API_KEY:
        opp["ai_verdict"] = "ANTHROPIC_API_KEY lipsă."
        return opp

    try:
        response = requests.post(
            ANTHROPIC_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": MODEL,
                "max_tokens": 300,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": _build_prompt(opp)}
                ]
            },
            timeout=30
        )

        if response.status_code != 200:
            log_warn(f"[Haiku] {ticker}: HTTP {response.status_code}")
            return opp

        data = response.json()
        text = data.get("content", [{}])[0].get("text", "")

        # Extrage JSON din răspuns
        json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            opp["ai_verdict"] = parsed.get("ai_verdict", "")
            opp["why_now"] = parsed.get("why_now", opp.get("why_now", ""))
            log_info(f"[Haiku] {ticker}: OK")
        else:
            log_warn(f"[Haiku] {ticker}: no JSON — {text[:80]}")

    except requests.Timeout:
        log_warn(f"[Haiku] {ticker}: timeout")
    except Exception as e:
        log_error(f"[Haiku] {ticker}: {e}")

    return opp


def enrich_with_haiku(opportunities: list[dict]) -> list[dict]:
    """
    Enrichează lista de oportunități cu ai_verdict și why_now în română.
    Rulează paralel cu ThreadPoolExecutor — ~5-10 secunde pentru 15 oportunități.
    """
    if not opportunities:
        return opportunities

    if not ANTHROPIC_API_KEY:
        log_warn("[Haiku] No ANTHROPIC_API_KEY — skipping")
        return opportunities

    log_info(f"[Haiku] Enriching {len(opportunities)} opportunities...")

    results = [None] * len(opportunities)

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_idx = {
                executor.submit(_enrich_single, opp): i
                for i, opp in enumerate(opportunities)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    log_error(f"[Haiku] Future error idx {idx}: {e}")
                    results[idx] = opportunities[idx]

        # Fill None cu originalele
        final = [r if r is not None else opportunities[i] for i, r in enumerate(results)]
        log_info(f"[Haiku] Done — {len(final)} opportunities enriched")
        return final

    except Exception as e:
        log_error(f"[Haiku] Enrichment failed: {e}")
        return opportunities
