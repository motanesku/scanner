# File: app/services/haiku_enricher.py
#
# Generează ai_verdict și why_now personalizat via Claude Haiku.
# Rulează paralel pentru toate oportunitățile din scan.
# Cost: ~$0.001 per scan (neglijabil).

import os
import json
import asyncio
import aiohttp
from app.utils.logger import log_info, log_warn, log_error

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """Ești un analist de investiții senior care scrie analize concise în limba română.
Stilul tău: direct, factual, fără exagerări. Maxim 2-3 propoziții per câmp.
Nu folosi bullet points. Nu repeta datele din input verbatim — interpretează-le."""


def _build_prompt(opp: dict) -> str:
    md = opp.get("market_data", {})
    price = md.get("price")
    volume = md.get("volume")
    vwap = md.get("vwap")
    transactions = md.get("transactions")

    trigger_stack = opp.get("trigger_stack", [])
    triggers_str = " + ".join(trigger_stack)

    # Context volume
    volume_context = ""
    if price and volume:
        turnover = price * volume / 1_000_000
        volume_context = f"Turnover zilnic: ${turnover:.1f}M."
    if vwap and price:
        diff_pct = ((price - vwap) / vwap) * 100
        direction = "peste" if diff_pct > 0 else "sub"
        volume_context += f" Close {direction} VWAP cu {abs(diff_pct):.1f}%."

    return f"""Analizează această oportunitate de investiție și generează:
1. "ai_verdict": teză de investiție în 2-3 propoziții (de ce e sau nu e interesant acum)
2. "why_now": context specific în 1-2 propoziții (ce se întâmplă concret acum cu această companie)

Date:
- Ticker: {opp.get('ticker')} — {opp.get('company')}
- Temă: {opp.get('theme')} / {opp.get('subtheme', 'N/A')}
- Rol: {opp.get('role')} | Semnal: {opp.get('signal')} | Scor: {opp.get('score')}
- Trigger stack: {triggers_str}
- Catalyst score: {opp.get('catalyst_score')} | Narrative score: {opp.get('narrative_score')} | Risk score: {opp.get('risk_score')}
- Preț: ${price} | Volum: {f"{volume:,}" if volume else "N/A"} shares
- {volume_context}

Răspunde STRICT în format JSON:
{{"ai_verdict": "...", "why_now": "..."}}"""


async def _enrich_single(session: aiohttp.ClientSession, opp: dict) -> dict:
    """Enrichează o singură oportunitate cu Haiku."""
    ticker = opp.get("ticker", "")

    if not ANTHROPIC_API_KEY:
        opp["ai_verdict"] = "API key lipsă."
        return opp

    try:
        payload = {
            "model": MODEL,
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": _build_prompt(opp)}
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }

        async with session.post(
            ANTHROPIC_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                log_warn(f"[Haiku] {ticker}: HTTP {resp.status} — {body[:100]}")
                return opp

            data = await resp.json()
            text = data.get("content", [{}])[0].get("text", "")

            # Parse JSON din răspuns
            # Haiku poate adăuga text în jurul JSON-ului
            import re
            json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                opp["ai_verdict"] = parsed.get("ai_verdict", "")
                opp["why_now"] = parsed.get("why_now", opp.get("why_now", ""))
                log_info(f"[Haiku] {ticker}: enriched OK")
            else:
                log_warn(f"[Haiku] {ticker}: no JSON in response — {text[:100]}")

    except asyncio.TimeoutError:
        log_warn(f"[Haiku] {ticker}: timeout")
    except Exception as e:
        log_error(f"[Haiku] {ticker}: error — {e}")

    return opp


async def _enrich_all_async(opportunities: list[dict]) -> list[dict]:
    """Enrichează toate oportunitățile în paralel."""
    # Limităm concurența la 5 requests simultan
    semaphore = asyncio.Semaphore(5)

    async def enrich_with_semaphore(session, opp):
        async with semaphore:
            return await _enrich_single(session, opp)

    async with aiohttp.ClientSession() as session:
        tasks = [enrich_with_semaphore(session, opp) for opp in opportunities]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Tratează excepțiile
    final = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log_error(f"[Haiku] Task {i} failed: {result}")
            final.append(opportunities[i])  # returnează original
        else:
            final.append(result)

    return final


def enrich_with_haiku(opportunities: list[dict]) -> list[dict]:
    """
    Enrichează lista de oportunități cu ai_verdict și why_now personalizat.
    Rulează async paralel — ~3-5 secunde pentru 15 oportunități.
    """
    if not opportunities:
        return opportunities

    if not ANTHROPIC_API_KEY:
        log_warn("[Haiku] No ANTHROPIC_API_KEY — skipping enrichment")
        return opportunities

    log_info(f"[Haiku] Enriching {len(opportunities)} opportunities...")

    try:
        # Rulează async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_enrich_all_async(opportunities))
        loop.close()
        log_info(f"[Haiku] Enrichment complete for {len(result)} opportunities")
        return result
    except Exception as e:
        log_error(f"[Haiku] Enrichment failed: {e}")
        return opportunities
