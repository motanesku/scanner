# File: app/collectors/volume_spike_collector.py
#
# Detectează volume spikes din grouped daily + history acumulat.
# Trigger real — indică activitate instituțională neobișnuită.
#
# Spike = volume_azi > avg_volume_20d × SPIKE_THRESHOLD
# Filtru: daily_turnover >= $5M (elimină micro-cap noise)

from app.collectors.volume_history import (
    get_volume_spike_ratio,
    get_avg_volume,
    load_history,
)
from app.models import Trigger
from app.utils.logger import log_info

# Threshold spike — volum dublu față de medie
SPIKE_THRESHOLD = 2.0

# Threshold pentru spike puternic
STRONG_SPIKE_THRESHOLD = 3.0

# Daily turnover minim pentru a considera spike-ul relevant
MIN_DAILY_TURNOVER = 5_000_000  # $5M


def collect_volume_spike_triggers(grouped_data: dict) -> list[Trigger]:
    """
    Detectează volume spikes din datele grouped daily curente.

    grouped_data = {ticker: bar} din Polygon grouped daily.
    Compară cu history acumulat local.

    Returnează lista de Trigger cu tip 'market'.
    """
    if not grouped_data:
        return []

    history = load_history()
    triggers = []
    checked = 0
    spikes_found = 0

    for ticker, bar in grouped_data.items():
        volume = bar.get("v")
        price = bar.get("c")  # close

        if not volume or not price:
            continue

        # Filtru turnover minim
        daily_turnover = price * volume
        if daily_turnover < MIN_DAILY_TURNOVER:
            continue

        checked += 1

        # Calculează ratio față de medie
        ratio = get_volume_spike_ratio(ticker, int(volume), history)

        if ratio is None:
            # Nu avem suficiente date istorice — skip
            continue

        if ratio < SPIKE_THRESHOLD:
            continue

        # Spike detectat
        spikes_found += 1
        avg_vol = get_avg_volume(ticker, history)

        urgency = "high" if ratio >= STRONG_SPIKE_THRESHOLD else "medium"
        confidence = min(10.0, 5.0 + (ratio - SPIKE_THRESHOLD) * 1.5)

        # Încearcă să detecteze direcția din vwap vs close
        vwap = bar.get("vw")
        close = bar.get("c")
        signal_side = "neutral"
        if vwap and close:
            if close > vwap * 1.005:
                signal_side = "buy"   # close peste vwap = presiune cumpărare
            elif close < vwap * 0.995:
                signal_side = "sell"  # close sub vwap = presiune vânzare

        headline = (
            f"{ticker} volume spike {ratio:.1f}x avg "
            f"({int(volume/1_000_000*10)/10}M vs avg {int(avg_vol/1_000_000*10)/10}M) "
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
                "ticker": ticker,
                "primary_ticker": ticker,
                "volume": int(volume),
                "avg_volume": int(avg_vol),
                "spike_ratio": round(ratio, 2),
                "price": price,
                "vwap": vwap,
                "daily_turnover": daily_turnover,
                "signal_side": signal_side,
                "trigger_category": "volume_spike",
                "entity_confidence": 10,
                "has_direct_event": True,
            }
        ))

    log_info(
        f"[VolumeSpike] Checked {checked} tickers with history → "
        f"{spikes_found} spikes found (threshold: {SPIKE_THRESHOLD}x)"
    )
    return triggers
