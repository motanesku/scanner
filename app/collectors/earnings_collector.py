def get_mock_earnings_schedule() -> dict:
    """
    Simulare simplă earnings proximity.
    """
    return {
        "FCX": {"days_to_earnings": 12},
        "SCCO": {"days_to_earnings": 19},
        "ETN": {"days_to_earnings": 8},
        "PANW": {"days_to_earnings": 14},
        "CRWD": {"days_to_earnings": 10},
        "ZS": {"days_to_earnings": 21},
        "VRT": {"days_to_earnings": 9},
        "ANET": {"days_to_earnings": 16},
        "SMCI": {"days_to_earnings": 7},
        "HUBB": {"days_to_earnings": 13}
    }
