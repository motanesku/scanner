# File: app/services/haiku_enricher.py

import os
import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.logger import log_info, log_warn, log_error

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"
MAX_WORKERS = 5

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

    role = opp.get("role", "")
    signal = opp.get("signal", "")
    theme = opp.get("theme", "")

    return f"""Analizează această oportunitate și generează în română 4 câmpuri:

1. "ai_verdict": teză de investiție în 2-3 propoziții (de ce e sau nu e interesant acum)
2. "why_now": context specific în 1-2 propoziții (ce se întâmplă concret acum)
3. "next_confirmations": listă cu exact 3 confirmări specifice necesare pentru {opp.get('ticker')} — ce trebuie să se întâmple concret pentru ca teza să se valideze
4. "failure_modes": listă cu exact 3 riscuri specifice pentru {opp.get('ticker')} — ce poate merge prost concret

Date:
- Ticker: {opp.get('ticker')} — {opp.get('company')}
- Temă: {theme} / {opp.get('subtheme', 'N/A')}
- Rol: {role} | Semnal: {signal} | Scor: {opp.get('score')}
- Trigger stack: {triggers_str}
- Catalyst: {opp.get('catalyst_score')} | Narrative: {opp.get('narrative_score')} | Risk: {opp.get('risk_score')}
- Preț: ${price} | Volum: {f"{volume:,}" if volume else "N/A"} shares
- {volume_context}

IMPORTANT pentru confirmări și riscuri:
- Scrie specific pentru {opp.get('ticker')} și {theme}, NU generic
- Menționează catalizatori concreți (earnings, guidance, volum, sector)
- Limbă română corectă, fraze scurte

Răspunde STRICT în format JSON fără text extra:
{{
  "ai_verdict": "...",
  "why_now": "...",
  "next_confirmations": ["confirmare 1 specifică", "confirmare 2 specifică", "confirmare 3 specifică"],
  "failure_modes": ["risc 1 specific", "risc 2 specific", "risc 3 specific"]
}}"""


def _enrich_single(opp: dict) -> dict:
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
                "max_tokens": 500,  # mai mult pentru 4 câmpuri
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

        # Extrage JSON — permite array-uri în interior
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            parsed = json.loads(json_match.group())
            if parsed.get("ai_verdict"):
                opp["ai_verdict"] = parsed["ai_verdict"]
            if parsed.get("why_now"):
                opp["why_now"] = parsed["why_now"]
            if parsed.get("next_confirmations") and isinstance(parsed["next_confirmations"], list):
                opp["next_confirmations"] = parsed["next_confirmations"][:3]
            if parsed.get("failure_modes") and isinstance(parsed["failure_modes"], list):
                opp["failure_modes"] = parsed["failure_modes"][:3]
            log_info(f"[Haiku] {ticker}: OK")
        else:
            log_warn(f"[Haiku] {ticker}: no JSON — {text[:80]}")

    except requests.Timeout:
        log_warn(f"[Haiku] {ticker}: timeout")
    except Exception as e:
        log_error(f"[Haiku] {ticker}: {e}")

    return opp


def enrich_with_haiku(opportunities: list[dict]) -> list[dict]:
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

        final = [r if r is not None else opportunities[i] for i, r in enumerate(results)]
        log_info(f"[Haiku] Done — {len(final)} opportunities enriched")
        return final

    except Exception as e:
        log_error(f"[Haiku] Enrichment failed: {e}")
        return opportunities
