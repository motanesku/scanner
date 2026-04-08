# File: app/engines/entity_resolver.py
#
# Rezolvă entități (companii) din text → ticker validat.
#
# Folosește ticker_universe.py ca sursă de adevăr.
# Niciodată regex pe cuvinte majuscule brute.

import re
from app.data.ticker_universe import build_universe, is_valid_ticker
from app.utils.logger import log_warn

# Pattern $TICKER explicit
DOLLAR_TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')

# Universe singleton — încărcat o dată per proces
_universe_cache = None


def get_universe() -> dict:
    """Returnează universe-ul curent (din cache sau fișier)."""
    global _universe_cache
    if _universe_cache is None:
        _universe_cache = build_universe()
    return _universe_cache


def refresh_universe() -> dict:
    """Forțează re-descărcarea universe-ului din Polygon."""
    global _universe_cache
    _universe_cache = build_universe(force=True)
    return _universe_cache


def resolve_tickers(text: str, max_results: int = 3) -> list[tuple[str, int]]:
    """
    Rezolvă tickere din text.
    Returnează lista de (ticker, entity_confidence).

    entity_confidence:
    - 10: $TICKER explicit + validat în universe
    - 8: nume companie din alias_index (match exact cu word boundary)
    - 0: nu s-a găsit nimic valid

    NICIODATĂ nu returnează cuvinte comune ca tickers.
    """
    universe = get_universe()
    alias_index = universe.get("alias_index", {})
    results = []
    seen = set()
    text_lower = text.lower()

    # 1. $TICKER explicit — cel mai precis
    dollar_matches = DOLLAR_TICKER_PATTERN.findall(text)
    for ticker in dollar_matches:
        ticker = ticker.upper()
        if ticker in seen:
            continue
        if is_valid_ticker(ticker, universe):
            seen.add(ticker)
            results.append((ticker, 10))
        else:
            # $TICKER menționat dar nu în universe — posibil OTC sau greșeală
            # Îl adăugăm cu confidence mai mic
            seen.add(ticker)
            results.append((ticker, 7))

    if len(results) >= max_results:
        return results[:max_results]

    # 2. Alias index — nume companie cu word boundary
    # Sortăm aliasurile după lungime descrescătoare pentru a evita
    # match-uri scurte care sunt subșiruri ale unor nume mai lungi
    # Ex: "nvidia" să nu fie găsit înainte de "nvidia corporation"
    matched_aliases = []
    for alias, ticker in alias_index.items():
        if ticker in seen:
            continue
        if len(alias) < 4:  # skip aliasuri foarte scurte
            continue
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, text_lower):
            matched_aliases.append((len(alias), alias, ticker))

    # Sortează: aliasuri mai lungi primul (mai specific)
    matched_aliases.sort(reverse=True)

    for _, alias, ticker in matched_aliases:
        if ticker in seen:
            continue
        seen.add(ticker)
        results.append((ticker, 8))

        if len(results) >= max_results:
            break

    return results[:max_results]


def validate_ticker(ticker: str) -> bool:
    """Verifică dacă un ticker e valid în universe."""
    return is_valid_ticker(ticker, get_universe())


def get_company_name(ticker: str) -> str | None:
    """Returnează numele oficial al companiei."""
    from app.data.ticker_universe import get_ticker_name
    return get_ticker_name(ticker, get_universe())
