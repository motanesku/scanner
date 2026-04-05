def get_mock_insider_activity() -> dict:
    """
    Simulare simplă de insider activity.
    Mai târziu înlocuim cu surse reale.
    """
    return {
        "FCX": {
            "has_insider_buy": True,
            "headline": "Insider accumulation detected",
            "confidence": 7.8
        },
        "PANW": {
            "has_insider_buy": False,
            "headline": "",
            "confidence": 0.0
        },
        "VRT": {
            "has_insider_buy": True,
            "headline": "Recent insider purchase cluster",
            "confidence": 8.1
        }
    }
