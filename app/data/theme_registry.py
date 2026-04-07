# File: app/data/theme_registry.py
#
# IMPORTANT: companiile au fost eliminate intentionat.
# Tickerele sunt descoperite dinamic din triggere reale:
# - SEC EDGAR Form 4 (insider buying)
# - SEC EDGAR 8-K Item 2.02 (earnings)
# - RSS news (mentions directe de ticker)
# - Polygon volume spikes (urmator)
#
# theme_registry contine doar:
# - keywords pentru detectia temei din text
# - subtheme labels pentru context

THEME_REGISTRY = {

    "AI Infrastructure Buildout": {
        "keywords": [
            "ai", "gpu", "datacenter", "data center", "inference",
            "training", "server", "compute", "cloud", "hyperscaler",
            "nvidia", "artificial intelligence", "llm", "foundation model"
        ],
        "subthemes": ["Compute", "Networking", "Cloud", "Power"],
    },

    "Semiconductors Cycle": {
        "keywords": [
            "semiconductor", "chip", "wafer", "fab", "foundry",
            "chipmaker", "node", "lithography", "packaging"
        ],
        "subthemes": ["Chips", "Manufacturing", "Equipment"],
    },

    "Energy & Commodities": {
        "keywords": [
            "oil", "gas", "lng", "energy", "commodity", "uranium",
            "nuclear", "copper", "mining", "crude", "brent", "wti"
        ],
        "subthemes": ["Oil", "Gas", "Uranium", "Copper"],
    },

    "Cybersecurity": {
        "keywords": [
            "cyber", "security", "ransomware", "breach", "firewall",
            "zero trust", "endpoint", "siem", "threat", "hack"
        ],
        "subthemes": ["Cloud Security", "Endpoint", "Identity"],
    },

    "Defense & Aerospace": {
        "keywords": [
            "defense", "military", "pentagon", "contract", "weapon",
            "missile", "drone", "aerospace", "navy", "army", "nato"
        ],
        "subthemes": ["Defense Spending", "Drones", "Space"],
    },

    "Biotech & Pharma": {
        "keywords": [
            "fda", "trial", "approval", "drug", "biotech", "clinical",
            "phase", "nda", "bla", "pdufa", "therapy", "oncology"
        ],
        "subthemes": ["FDA Catalysts", "Oncology", "Gene Therapy"],
    },

    "General Market": {
        "keywords": [],
        "subthemes": ["Macro"],
    }
}
