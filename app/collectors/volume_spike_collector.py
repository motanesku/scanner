# File: app/collectors/volume_spike_collector.py
#
# Detectează volume spikes comparând volumul curent cu media istorică din D1.
# Trigger real — indică activitate instituțională neobișnuită.

from app.collectors.volume_history import get_volume_history, get_volume_spike_ratio
from app.models import Trigger
from app.utils.logger import log_info

SPIKE_THRESHOLD        = 2.0   # volum dublu față de medie
STRONG_SPIKE_THRESHOLD = 3.0   # volum triplu — semnal puternic
MIN_DAILY_TURNOVER     = 5_000_000  # $5M — elimină micro-cap


def collect_volume_spike_triggers(
    grouped_data: dict,
    tickers_to_check: list[str] | None = None,
) -> list[Trigger]:
    """
    Detectează volume spikes din grouped daily vs. history D1.

    grouped_data = {ticker: bar} din Polygon grouped daily.
    tickers_to_check = lista de tickers de verificat (din scan).
                       Dacă None, verifică toți tickerii din grouped_data.
    """
    if not grouped_data:
        return []

    # Dacă avem o listă specifică, verificăm doar aceia
    # altfel verificăm toți tickerii cu turnover suficient
    if tickers_to_check:
        candidates = {t: grouped_data[t] for t in tickers_to_check if t in grouped_data}
    else:
        candidates = {
            t: bar for t, bar in grouped_data.items()
            if (bar.get("c", 0) * bar.get("v", 0)) >= MIN_DAILY_TURNOVER
        }

    if not candidates:
        return []

    # Fetch history din D1 pentru toți candidații
    history = get_volume_history(list(candidates.keys()), days=20)
    log_info(f"[VolumeSpike] Checking {len(candidates)} tickers, history available for {len(history)}")

    triggers = []
    spikes_found = 0

    for ticker, bar in candidates.items():
        volume  = bar.get("v", 0)
        close   = bar.get("c", 0)
        vwap    = bar.get("vw", 0)

        if not volume or not close:
            continue

        # Filtru turnover minim
        if close * volume < MIN_DAILY_TURNOVER:
            continue

        # Calculează spike ratio față de medie istorică
        ratio = get_volume_spike_ratio(ticker, int(volume), history)

        if ratio is None:
            continue  # nu avem suficiente date istorice (< 5 zile)

        if ratio < SPIKE_THRESHOLD:
            continue  # nu e spike

        spikes_found += 1

        # Detectează direcția din vwap vs close
        signal_side = "neutral"
        if vwap and close:
            if close > vwap * 1.005:
                signal_side = "buy"    # close peste vwap = presiune cumpărare
            elif close < vwap * 0.995:
                signal_side = "sell"   # close sub vwap = presiune vânzare

        urgency    = "high" if ratio >= STRONG_SPIKE_THRESHOLD else "medium"
        confidence = min(10.0, 5.0 + (ratio - SPIKE_THRESHOLD) * 1.5)

        # Calculează media pentru mesaj
        from app.collectors.volume_history import get_avg_volume
        avg_vol = get_avg_volume(ticker, history) or 0

        headline = (
            f"{ticker} volume spike {ratio:.1f}x avg "
            f"({_fmt_vol(int(volume))} vs avg {_fmt_vol(int(avg_vol))}) "
            f"— {signal_side} pressure"
        )

        triggers.append(Trigger(
            trigger_type="market",
            headline=headline,
            theme_hint="General Market",
            subthemes=["Volume Spike"],
            urgency=urgency,
            freshness="new",
            confidence=confidence,
            metadata={
                "ticker":           ticker,
                "primary_ticker":   ticker,
                "volume":           int(volume),
                "avg_volume":       int(avg_vol),
                "spike_ratio":      round(ratio, 2),
                "price":            close,
                "vwap":             vwap,
                "daily_turnover":   close * volume,
                "signal_side":      signal_side,
                "trigger_category": "volume_spike",
                "entity_confidence": 10,
                "has_direct_event": True,
            }
        ))

    log_info(
        f"[VolumeSpike] {spikes_found} spikes found "
        f"(threshold: {SPIKE_THRESHOLD}x, checked: {len(candidates)})"
    )
    return triggers


def _fmt_vol(v: int) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)
