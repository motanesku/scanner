# File: app/data/theme_registry.py

THEME_REGISTRY = {

    "AI Infrastructure Buildout": {
        "keywords": [
            "ai", "gpu", "datacenter", "inference", "training",
            "server", "compute", "cloud", "hyperscaler"
        ],
        "subthemes": ["Compute", "Networking", "Cloud"],
        "companies": [
            {"ticker": "NVDA", "company_name": "Nvidia", "role": "Leader", "positioning": "AI Compute", "horizon": "Position", "market_cap_bucket": "Large Cap"},
            {"ticker": "AMD", "company_name": "AMD", "role": "Challenger", "positioning": "AI Compute", "horizon": "Position", "market_cap_bucket": "Large Cap"},
            {"ticker": "SMCI", "company_name": "Super Micro", "role": "Infra", "positioning": "Servers", "horizon": "Swing", "market_cap_bucket": "Large Cap"},
            {"ticker": "ANET", "company_name": "Arista", "role": "Infra", "positioning": "Networking", "horizon": "Position", "market_cap_bucket": "Large Cap"}
        ]
    },

    "Semiconductors Cycle": {
        "keywords": [
            "semiconductor", "chip", "wafer", "fab", "foundry"
        ],
        "subthemes": ["Chips", "Manufacturing"],
        "companies": [
            {"ticker": "TSM", "company_name": "TSMC", "role": "Foundry", "positioning": "Core Supplier", "horizon": "Position", "market_cap_bucket": "Large Cap"},
            {"ticker": "INTC", "company_name": "Intel", "role": "Legacy", "positioning": "Turnaround", "horizon": "Swing", "market_cap_bucket": "Large Cap"}
        ]
    },

    "Energy & Commodities": {
        "keywords": [
            "oil", "gas", "lng", "energy", "commodity", "uranium"
        ],
        "subthemes": ["Oil", "Gas", "Uranium"],
        "companies": [
            {"ticker": "XOM", "company_name": "Exxon", "role": "Major", "positioning": "Oil", "horizon": "Position", "market_cap_bucket": "Large Cap"},
            {"ticker": "CCJ", "company_name": "Cameco", "role": "Uranium", "positioning": "Nuclear", "horizon": "Position", "market_cap_bucket": "Mid Cap"}
        ]
    },

    "Cybersecurity": {
        "keywords": [
            "cyber", "security", "ransomware", "breach"
        ],
        "subthemes": ["Cloud Security"],
        "companies": [
            {"ticker": "CRWD", "company_name": "CrowdStrike", "role": "Leader", "positioning": "Security", "horizon": "Position", "market_cap_bucket": "Large Cap"},
            {"ticker": "PANW", "company_name": "Palo Alto", "role": "Leader", "positioning": "Security", "horizon": "Position", "market_cap_bucket": "Large Cap"}
        ]
    },

    "General Market": {
        "keywords": [],
        "subthemes": ["Macro"],
        "companies": [
            {"ticker": "SPY", "company_name": "S&P 500 ETF", "role": "Macro Proxy", "positioning": "Market", "horizon": "Swing", "market_cap_bucket": "Large Cap"}
        ]
    }
}
