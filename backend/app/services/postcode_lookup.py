import re

# Maps postcode area prefix (letters only, before first digit) to UK region.
# Covers all Royal Mail postcode areas. Region names match ONS standard geography.
_AREA_TO_REGION: dict[str, str] = {
    # London (includes inner and outer London postal areas)
    "E": "London", "EC": "London", "N": "London", "NW": "London",
    "SE": "London", "SW": "London", "W": "London", "WC": "London",
    "BR": "London", "CR": "London", "DA": "London", "EN": "London",
    "HA": "London", "IG": "London", "KT": "London", "RM": "London",
    "SM": "London", "TW": "London", "UB": "London",
    # South East
    "BN": "South East", "CT": "South East", "GU": "South East",
    "HP": "South East", "ME": "South East", "MK": "South East",
    "OX": "South East", "PO": "South East", "RG": "South East",
    "RH": "South East", "SL": "South East", "SO": "South East",
    "TN": "South East",
    # South West
    "BA": "South West", "BH": "South West", "BS": "South West",
    "DT": "South West", "EX": "South West", "GL": "South West",
    "PL": "South West", "SN": "South West", "SP": "South West",
    "TA": "South West", "TQ": "South West", "TR": "South West",
    # East of England
    "AL": "East of England", "CB": "East of England", "CM": "East of England",
    "CO": "East of England", "IP": "East of England", "LU": "East of England",
    "NR": "East of England", "PE": "East of England", "SG": "East of England",
    "SS": "East of England", "WD": "East of England",
    # West Midlands
    "B": "West Midlands", "CV": "West Midlands", "DY": "West Midlands",
    "HR": "West Midlands", "ST": "West Midlands", "TF": "West Midlands",
    "WR": "West Midlands", "WS": "West Midlands", "WV": "West Midlands",
    "SY": "West Midlands",
    # East Midlands
    "DE": "East Midlands", "LE": "East Midlands", "LN": "East Midlands",
    "NG": "East Midlands", "NN": "East Midlands",
    # North West
    "BB": "North West", "BL": "North West", "CA": "North West",
    "CH": "North West", "CW": "North West", "FY": "North West",
    "L": "North West", "LA": "North West", "M": "North West",
    "OL": "North West", "PR": "North West", "SK": "North West",
    "WA": "North West", "WN": "North West",
    # North East
    "DH": "North East", "DL": "North East", "NE": "North East",
    "SR": "North East", "TS": "North East",
    # Yorkshire and the Humber
    "BD": "Yorkshire and the Humber", "DN": "Yorkshire and the Humber",
    "HD": "Yorkshire and the Humber", "HG": "Yorkshire and the Humber",
    "HU": "Yorkshire and the Humber", "HX": "Yorkshire and the Humber",
    "LS": "Yorkshire and the Humber", "S": "Yorkshire and the Humber",
    "WF": "Yorkshire and the Humber", "YO": "Yorkshire and the Humber",
    # Scotland
    "AB": "Scotland", "DD": "Scotland", "DG": "Scotland", "EH": "Scotland",
    "FK": "Scotland", "G": "Scotland", "HS": "Scotland", "IV": "Scotland",
    "KA": "Scotland", "KW": "Scotland", "KY": "Scotland", "ML": "Scotland",
    "PA": "Scotland", "PH": "Scotland", "TD": "Scotland", "ZE": "Scotland",
    # Wales
    "CF": "Wales", "LD": "Wales", "LL": "Wales", "NP": "Wales", "SA": "Wales",
    # Northern Ireland
    "BT": "Northern Ireland",
}

_OUTWARD_RE = re.compile(r'^[A-Z]{1,2}[0-9][A-Z0-9]?$')


def validate_postcode_outward(value: str) -> bool:
    """Return True if value matches the UK outward code format (e.g. M1, SW1A)."""
    return bool(_OUTWARD_RE.match(value.strip().upper()))


def get_region_from_postcode(postcode_outward: str | None) -> str | None:
    """Derive UK region from outward code. Returns None if unrecognized."""
    if not postcode_outward:
        return None
    area_match = re.match(r'^([A-Za-z]+)', postcode_outward.strip())
    if not area_match:
        return None
    area = area_match.group(1).upper()
    return _AREA_TO_REGION.get(area)
