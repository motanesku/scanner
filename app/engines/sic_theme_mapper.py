# File: app/engines/sic_theme_mapper.py
#
# Mapează SIC codes → teme investabile + flag de excludere.
#
# SIC (Standard Industrial Classification) e disponibil în Polygon
# /v3/reference/tickers și ne permite să:
# 1. Asignăm tema corectă per companie (nu din RSS)
# 2. Excludem sectoare irelevante (REIT, food, fashion etc.)
#
# Referință SIC: https://www.osha.gov/data/sics

# ── Sectoare EXCLUSE complet ──────────────────────────────────────
# Acestea nu apar niciodată în scanner indiferent de earnings/news

EXCLUDED_SIC_RANGES = [
    # Real Estate & REITs
    (6500, 6599),
    (6798, 6799),
    # Hotels, Motels, Restaurants, Food Service
    (5810, 5819),
    (7000, 7099),
    # Retail — fashion, food, general merchandise
    (5600, 5699),  # apparel stores
    (5400, 5499),  # food stores
    (5900, 5999),  # misc retail
    # Agriculture, Fishing, Forestry
    (100, 999),
    # Mining non-strategic (coal, generic mining)
    (1200, 1499),
    # Construction generic
    (1500, 1799),
    # Textile, Apparel Manufacturing
    (2200, 2399),
    # Food & Beverage Manufacturing
    (2000, 2199),
    # Printing, Publishing
    (2700, 2799),
    # Furniture
    (2500, 2599),
    # Closed-end funds, investment trusts non-strategic
    (6726, 6726),
    (6199, 6199),
]

EXCLUDED_SIC_EXACT = {
    6726,   # Investment offices (closed-end funds)
    6199,   # Finance services generic
    6311,   # Life insurance
    6321,   # Accident and health insurance
    6411,   # Insurance agents
    6552,   # Land subdividers & developers
    5812,   # Eating places (restaurants)
    5411,   # Grocery stores
    7011,   # Hotels and motels
    2111,   # Cigarettes
    2100,   # Tobacco products
}

# ── Mapare SIC → Temă ─────────────────────────────────────────────

SIC_TO_THEME = {

    # ── Semiconductori ───────────────────────────────────────────
    3674: ("Semiconductori & Chips", "Fabricație"),
    3672: ("Semiconductori & Chips", "PCB & Hardware"),
    3679: ("Semiconductori & Chips", "Electronic Components"),
    3825: ("Semiconductori & Chips", "Test Equipment"),  # AEHR e aici
    3827: ("Semiconductori & Chips", "Optical Instruments"),
    3699: ("Semiconductori & Chips", "Electronic Components"),
    3669: ("Semiconductori & Chips", "Communications Equipment"),

    # ── AI / Software / Cloud ─────────────────────────────────────
    7372: ("AI Infrastructure Buildout", "Software"),
    7371: ("AI Infrastructure Buildout", "IT Services"),
    7374: ("AI Infrastructure Buildout", "Data Processing"),
    7379: ("AI Infrastructure Buildout", "Computer Services"),
    7389: ("AI Infrastructure Buildout", "Business Services"),
    3577: ("AI Infrastructure Buildout", "Computer Peripherals"),
    3571: ("AI Infrastructure Buildout", "Computers"),
    3572: ("AI Infrastructure Buildout", "Storage"),
    3669: ("AI Infrastructure Buildout", "Networking"),

    # ── Telecomunicații / Networking ──────────────────────────────
    4813: ("AI Infrastructure Buildout", "Telecom"),
    4812: ("AI Infrastructure Buildout", "Telecom Wireless"),
    3661: ("AI Infrastructure Buildout", "Telecom Equipment"),
    3663: ("AI Infrastructure Buildout", "Broadcast Equipment"),
    3672: ("AI Infrastructure Buildout", "Networking Hardware"),

    # ── Energy ───────────────────────────────────────────────────
    1311: ("Energy & Commodities", "Oil & Gas E&P"),
    1321: ("Energy & Commodities", "Natural Gas"),
    2911: ("Energy & Commodities", "Oil Refining"),
    4911: ("Energy & Commodities", "Electric Utilities"),
    4931: ("Energy & Commodities", "Electric & Gas Utilities"),
    4941: ("Energy & Commodities", "Water Utilities"),
    4924: ("Energy & Commodities", "Natural Gas Distribution"),  # OGS e aici
    4922: ("Energy & Commodities", "Natural Gas Transmission"),
    1381: ("Energy & Commodities", "Drilling"),
    1389: ("Energy & Commodities", "Oil Field Services"),
    5171: ("Energy & Commodities", "Petroleum Distribution"),

    # ── Nuclear / Uranium ─────────────────────────────────────────
    1094: ("Energy & Commodities", "Uranium Mining"),
    4911: ("Energy & Commodities", "Nuclear Power"),

    # ── Renewable Energy ──────────────────────────────────────────
    3559: ("Energy & Commodities", "Solar Equipment"),
    3674: ("Energy & Commodities", "Solar Cells"),  # overlap cu semis

    # ── Defense & Aerospace ──────────────────────────────────────
    3812: ("Defense & Aerospace", "Defense Electronics"),
    3769: ("Defense & Aerospace", "Missiles & Space"),
    3728: ("Defense & Aerospace", "Aircraft Parts"),
    3721: ("Defense & Aerospace", "Aircraft"),
    3761: ("Defense & Aerospace", "Guided Missiles"),
    3489: ("Defense & Aerospace", "Ordnance"),
    3812: ("Defense & Aerospace", "Defense Systems"),
    7812: ("Defense & Aerospace", "Simulation & Training"),

    # ── Biotech & Pharma ─────────────────────────────────────────
    2836: ("Biotech & Pharma", "Biologicals"),
    2835: ("Biotech & Pharma", "Diagnostics"),
    2830: ("Biotech & Pharma", "Pharma"),
    2833: ("Biotech & Pharma", "Pharma"),
    2834: ("Biotech & Pharma", "Pharma"),
    8731: ("Biotech & Pharma", "R&D"),
    2860: ("Biotech & Pharma", "Industrial Chemicals"),
    5047: ("Biotech & Pharma", "Medical Supplies"),
    5122: ("Biotech & Pharma", "Drug Distribution"),
    3841: ("Biotech & Pharma", "Medical Instruments"),
    3845: ("Biotech & Pharma", "Electromedical"),
    3826: ("Biotech & Pharma", "Lab Instruments"),

    # ── Copper & Critical Metals ─────────────────────────────────
    1040: ("Metals & Mining", "Gold Mining"),
    1090: ("Metals & Mining", "Metal Mining"),
    3330: ("Metals & Mining", "Copper Smelting"),
    3350: ("Metals & Mining", "Rolling Mills"),
    1000: ("Metals & Mining", "Metal Mining"),
    1020: ("Metals & Mining", "Copper Mining"),

    # ── Fintech / Crypto ─────────────────────────────────────────
    6099: ("Fintech & Crypto", "Financial Services"),
    6141: ("Fintech & Crypto", "Personal Credit"),
    6159: ("Fintech & Crypto", "Federal Credit"),
    6211: ("Fintech & Crypto", "Security Brokers"),
    6282: ("Fintech & Crypto", "Investment Advice"),

    # ── Industrial / Infrastructure ───────────────────────────────
    3559: ("Industrial & Infrastructure", "Industrial Machinery"),
    3443: ("Industrial & Infrastructure", "Fabricated Plate Work"),
    3444: ("Industrial & Infrastructure", "Sheet Metal"),
    3490: ("Industrial & Infrastructure", "Metal Services"),
    3790: ("Industrial & Infrastructure", "Transportation Equipment"),
    4011: ("Industrial & Infrastructure", "Railroads"),  # GBX e aici
    4400: ("Industrial & Infrastructure", "Water Transportation"),
    3743: ("Industrial & Infrastructure", "Railroad Equipment"),

    # ── EV / Auto ─────────────────────────────────────────────────
    3711: ("EV & Mobility", "Motor Vehicles"),
    3714: ("EV & Mobility", "Motor Vehicle Parts"),
    3716: ("EV & Mobility", "Motor Homes"),
    3559: ("EV & Mobility", "EV Equipment"),
    5511: ("EV & Mobility", "Auto Dealers"),

    # ── Cybersecurity ─────────────────────────────────────────────
    # Cybersecurity e subset al 7372 — diferențierea e din company name
    # Tratăm separat în entity resolver dacă avem keywords

}

# ── Ticker overrides — forțează tema indiferent de SIC ───────────
# Folosit pentru companii known din portofoliu sau watchlist

TICKER_THEME_OVERRIDE = {
    # Portofoliu actual
    "MU":   ("Semiconductori & Chips", "Memory"),
    "CRDO": ("Semiconductori & Chips", "Connectivity"),
    "ALAB": ("AI Infrastructure Buildout", "Interconnect"),
    "CEG":  ("Energy & Commodities", "Nuclear"),
    "CLS":  ("AI Infrastructure Buildout", "Manufacturing"),
    "ERO":  ("Metals & Mining", "Copper"),
    "MARA": ("Fintech & Crypto", "Bitcoin Mining"),
    "ACHR": ("EV & Mobility", "eVTOL"),
    "PATH": ("AI Infrastructure Buildout", "AI Software"),
    "INOD": ("AI Infrastructure Buildout", "AI Data"),

    # Watchlist
    "NVDA": ("Semiconductori & Chips", "GPU"),
    "AMD":  ("Semiconductori & Chips", "CPU/GPU"),
    "INTC": ("Semiconductori & Chips", "CPU"),
    "APP":  ("AI Infrastructure Buildout", "AI Advertising"),
    "AEHR": ("Semiconductori & Chips", "Test Equipment"),
    "INSM": ("Biotech & Pharma", "Rare Disease"),
    "GOOGL":("AI Infrastructure Buildout", "Cloud/AI"),
    "MSFT": ("AI Infrastructure Buildout", "Cloud/AI"),
    "AMZN": ("AI Infrastructure Buildout", "Cloud"),
    "META": ("AI Infrastructure Buildout", "Social AI"),
    "TSLA": ("EV & Mobility", "EV"),
    "PLTR": ("AI Infrastructure Buildout", "Defense AI"),
    "PANW": ("Cybersecurity", "NGFW"),
    "CRWD": ("Cybersecurity", "EDR"),
    "NET":  ("Cybersecurity", "Cloud Security"),
    "GBX":  ("Industrial & Infrastructure", "Rail Cars"),
    "OGS":  ("Energy & Commodities", "Natural Gas"),
    "LEVI": None,   # exclude explicit
    "WW":   None,   # exclude explicit (bankruptcy)
    "KRUS": None,   # exclude explicit (sushi)
    "FCPT": None,   # exclude explicit (REIT)
    "EPRT": None,   # exclude explicit (REIT)
    "DOLE": None,   # exclude explicit (food)
    "CPPTL": None,  # exclude explicit (pass-through trust)
}


def get_theme_for_ticker(ticker: str, sic_code: int | None = None) -> tuple[str, str] | None:
    """
    Returnează (tema, subtema) pentru un ticker.

    Prioritate:
    1. TICKER_THEME_OVERRIDE — forțat manual (None = exclus)
    2. SIC code → tema
    3. None — tema necunoscută (va folosi fallback RSS)
    """
    ticker = ticker.upper()

    # 1. Override manual
    if ticker in TICKER_THEME_OVERRIDE:
        result = TICKER_THEME_OVERRIDE[ticker]
        return result  # poate fi None (exclus explicit)

    # 2. SIC code
    if sic_code:
        if is_excluded_sic(sic_code):
            return None  # exclus
        if sic_code in SIC_TO_THEME:
            return SIC_TO_THEME[sic_code]

    return ("General Market", "Macro")  # fallback — va fi filtrat dacă scorul e mic


def is_excluded_sic(sic_code: int) -> bool:
    """Returnează True dacă SIC code-ul indică un sector exclus."""
    if sic_code in EXCLUDED_SIC_EXACT:
        return True
    for start, end in EXCLUDED_SIC_RANGES:
        if start <= sic_code <= end:
            return True
    return False


def is_investable_sector(ticker: str, sic_code: int | None = None) -> bool:
    """
    Verifică rapid dacă un ticker e dintr-un sector investabil.
    False = exclus complet din scanner.
    """
    result = get_theme_for_ticker(ticker, sic_code)
    return result is not None
