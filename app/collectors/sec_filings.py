# File: app/collectors/sec_filings.py

import requests
from datetime import datetime, timedelta

SEC_HEADERS = {
    "User-Agent": "scanner-mvp/1.0 your-email@example.com"
}

SEC_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


def collect_filings(days_back: int = 3, max_results: int = 30):
    """
    Colectează filing-uri SEC recente (8-K, S-3, 424B, etc.) din EDGAR Atom feed.
    Returnează o listă simplificată de filing-uri.
    """

    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "action": "getcurrent",
        "CIK": "",
        "type": "",
        "company": "",
        "dateb": "",
        "owner": "include",
        "start": "0",
        "count": str(max_results),
        "output": "atom"
    }

    try:
        response = requests.get(SEC_FEED_URL, headers=SEC_HEADERS, params=params, timeout=20)
        response.raise_for_status()
        xml_text = response.text

        # Parsing simplu fără librării externe suplimentare
        entries = xml_text.split("<entry>")
        filings = []

        for entry in entries[1:]:
            try:
                title = _extract_between(entry, "<title>", "</title>")
                updated = _extract_between(entry, "<updated>", "</updated>")
                link = _extract_between(entry, '<link href="', '"')
                summary = _extract_between(entry, "<summary>", "</summary>")

                filing = {
                    "title": title.strip() if title else "",
                    "updated": updated.strip() if updated else "",
                    "link": link.strip() if link else "",
                    "summary": summary.strip() if summary else "",
                    "source": "SEC"
                }

                filings.append(filing)

            except Exception:
                continue

        return filings

    except Exception as e:
        return [{
            "title": "SEC collector error",
            "updated": "",
            "link": "",
            "summary": str(e),
            "source": "SEC"
        }]


def _extract_between(text: str, start: str, end: str):
    try:
        s = text.index(start) + len(start)
        e = text.index(end, s)
        return text[s:e]
    except ValueError:
        return ""
