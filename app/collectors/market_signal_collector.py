def get_mock_market_signals() -> dict:
    """
    Simulare simplă de market confirmation.
    """
    return {
        "FCX": {
            "relative_strength": "Improving",
            "volume_confirmation": True,
            "price_structure": "Constructive"
        },
        "ETN": {
            "relative_strength": "Strong",
            "volume_confirmation": True,
            "price_structure": "Constructive"
        },
        "PANW": {
            "relative_strength": "Neutral",
            "volume_confirmation": False,
            "price_structure": "Range-bound"
        },
        "CRWD": {
            "relative_strength": "Improving",
            "volume_confirmation": True,
            "price_structure": "Constructive"
        },
        "VRT": {
            "relative_strength": "Strong",
            "volume_confirmation": True,
            "price_structure": "Constructive"
        },
        "ANET": {
            "relative_strength": "Strong",
            "volume_confirmation": False,
            "price_structure": "Extended"
        }
    }
