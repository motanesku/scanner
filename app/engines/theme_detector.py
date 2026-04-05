# File: app/engines/theme_detector.py

from app.data.theme_registry import THEME_REGISTRY


def detect_theme_from_text(text: str):
    text_lower = text.lower()

    best_theme = None
    best_score = 0
    matched_subthemes = []

    for theme_name, theme_data in THEME_REGISTRY.items():
        score = 0

        for kw in theme_data["keywords"]:
            if kw in text_lower:
                score += 1

        if score > best_score:
            best_score = score
            best_theme = theme_name
            matched_subthemes = theme_data.get("subthemes", [])

    # 🔥 IMPORTANT: fallback dacă nu găsește nimic
    if best_theme is None:
        return "General Market", ["Macro"], 4.5

    confidence = min(9.5, 5.0 + best_score)

    return best_theme, matched_subthemes, confidence
