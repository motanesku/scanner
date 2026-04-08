# File: app/engines/sic_theme_mapper.py
#
# Mapează SIC codes → teme investabile.
# SIC e adus din SEC EDGAR per ticker la fiecare scan.
#
# FILOZOFIE:
# - SIC asignează tema corectă — nu filtrează
# - Insider buy NICIODATĂ nu se pierde indiferent de SIC
# - Tema "General Market" e fallback valid — nu excludem

# ── Mapare SIC → Temă ─────────────────────────────────────────────

SIC_TO_THEME = {

    # ── Semiconductori ───────────────────────────────────────────
    3674: ("Semiconductori & Chips", "Fabricație"),
    3672: ("Semiconductori & Chips", "PCB & Hardware"),
    3679: ("Semiconductori & Chips", "Electronic Components"),
    3825: ("Semiconductori & Chips", "Test Equipment"),   # AEHR
    3827: ("Semiconductori & Chips", "Optical Instruments"),
    3699: ("Semiconductori & Chips", "Electronic Components"),
    3559: ("Semiconductori & Chips", "Industrial Equipment"),

    # ── AI / Software / Cloud ─────────────────────────────────────
    7372: ("AI Infrastructure Buildout", "Software"),
    7371: ("AI Infrastructure Buildout", "IT Services"),
    7374: ("AI Infrastructure Buildout", "Data Processing"),
    7375: ("AI Infrastructure Buildout", "Internet Services"),  # IAC
    7379: ("AI Infrastructure Buildout", "Computer Services"),
    7389: ("AI Infrastructure Buildout", "Business Services"),
    3577: ("AI Infrastructure Buildout", "Computer Peripherals"),
    3571: ("AI Infrastructure Buildout", "Computers"),
    3572: ("AI Infrastructure Buildout", "Storage"),

    # ── Telecomunicații / Networking ──────────────────────────────
    # SIC 3663 e Broadcast Equipment — Telecom, nu AI direct
    4813: ("Telecom & Networking", "Telecom"),
    4812: ("Telecom & Networking", "Telecom Wireless"),
    3661: ("Telecom & Networking", "Telecom Equipment"),
    3663: ("Telecom & Networking", "Broadcast Equipment"),   # VISN
    3669: ("Telecom & Networking", "Communications Equipment"),

    # ── Energy ───────────────────────────────────────────────────
    1311: ("Energy & Commodities", "Oil & Gas E&P"),
    1321: ("Energy & Commodities", "Natural Gas"),
    2911: ("Energy & Commodities", "Oil Refining"),          # XOM
    4911: ("Energy & Commodities", "Electric Utilities"),
    4931: ("Energy & Commodities", "Electric & Gas Utilities"),
    4941: ("Energy & Commodities", "Water Utilities"),
    4924: ("Energy & Commodities", "Natural Gas Distribution"),  # OGS
    4922: ("Energy & Commodities", "Natural Gas Transmission"),
    1381: ("Energy & Commodities", "Drilling"),
    1389: ("Energy & Commodities", "Oil Field Services"),
    5171: ("Energy & Commodities", "Petroleum Distribution"),

    # ── Nuclear / Uranium ─────────────────────────────────────────
    1094: ("Energy & Commodities", "Uranium Mining"),

    # ── Defense & Aerospace ──────────────────────────────────────
    3812: ("Defense & Aerospace", "Defense Electronics"),
    3769: ("Defense & Aerospace", "Missiles & Space"),
    3728: ("Defense & Aerospace", "Aircraft Parts"),
    3721: ("Defense & Aerospace", "Aircraft"),
    3761: ("Defense & Aerospace", "Guided Missiles"),
    3489: ("Defense & Aerospace", "Ordnance"),

    # ── Biotech & Pharma ─────────────────────────────────────────
    2836: ("Biotech & Pharma", "Biologicals"),
    2835: ("Biotech & Pharma", "Diagnostics"),
    2830: ("Biotech & Pharma", "Pharma"),
    2833: ("Biotech & Pharma", "Pharma"),
    2834: ("Biotech & Pharma", "Pharma"),                    # NRIX
    8731: ("Biotech & Pharma", "R&D"),
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
    1020: ("Metals & Mining", "Copper Mining"),
    1000: ("Metals & Mining", "Metal Mining"),

    # ── Fintech / Crypto ─────────────────────────────────────────
    6099: ("Fintech & Crypto", "Financial Services"),
    6141: ("Fintech & Crypto", "Personal Credit"),
    6211: ("Fintech & Crypto", "Security Brokers"),
    6282: ("Fintech & Crypto", "Investment Advice"),

    # ── Industrial / Infrastructure ───────────────────────────────
    4011: ("Industrial & Infrastructure", "Railroads"),      # GBX
    3743: ("Industrial & Infrastructure", "Railroad Equipment"),
    3711: ("Industrial & Infrastructure", "Motor Vehicles"),
    3714: ("Industrial & Infrastructure", "Motor Vehicle Parts"),
    3443: ("Industrial & Infrastructure", "Fabricated Plate Work"),
    3790: ("Industrial & Infrastructure", "Transportation Equipment"),

    # ── EV / Mobility ─────────────────────────────────────────────
    3716: ("EV & Mobility", "Motor Homes"),

    # ── Transportation ────────────────────────────────────────────
    4512: ("Transportation", "Airlines"),                    # DAL
    4400: ("Transportation", "Water Transportation"),
    4210: ("Transportation", "Trucking"),
    4011: ("Transportation", "Railroads"),

    # ── Retail ────────────────────────────────────────────────────
    5941: ("Retail & Consumer", "Sporting Goods"),           # ASO
    5731: ("Retail & Consumer", "Electronics Stores"),
    5511: ("Retail & Consumer", "Auto Dealers"),
    5912: ("Retail & Consumer", "Drug Stores"),

    # ── Cybersecurity ─────────────────────────────────────────────
    # Subset al 7372 — diferențierea e din company name/override
}

# ── Ticker overrides — forțează tema indiferent de SIC ───────────
# Folosit pentru companii known din portofoliu sau watchlist
# None = nicio excludere — excluderea nu se face pe temă

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
    "XOM":  ("Energy & Commodities", "Oil & Gas"),
    "DAL":  ("Transportation", "Airlines"),
    "IAC":  ("AI Infrastructure Buildout", "Internet/Media"),
}


def get_theme_for_ticker(ticker: str, sic_code: int | None = None) -> tuple[str, str] | None:
    """
    Returnează (tema, subtema) pentru un ticker.

    Prioritate:
    1. TICKER_THEME_OVERRIDE — forțat manual
    2. SIC code → tema
    3. ("General Market", "Macro") — fallback

    NICIODATĂ nu returnează None pentru a exclude un ticker.
    Excluderea e responsabilitatea filtrelor de calitate (turnover, trigger).
    """
    ticker = ticker.upper()

    # 1. Override manual
    if ticker in TICKER_THEME_OVERRIDE:
        return TICKER_THEME_OVERRIDE[ticker]

    # 2. SIC code
    if sic_code and sic_code in SIC_TO_THEME:
        return SIC_TO_THEME[sic_code]

    # 3. Fallback — General Market e valid
    return ("General Market", "Macro")


def get_theme_for_insider(ticker: str, sic_code: int | None = None) -> tuple[str, str]:
    """
    Returnează tema pentru un insider trigger.
    NICIODATĂ nu exclude un insider buy — e cel mai valoros semnal.
    Returnează întotdeauna o temă validă.
    """
    result = get_theme_for_ticker(ticker, sic_code)
    return result if result else ("General Market", "Macro")
