import httpx
from bs4 import BeautifulSoup
from carbon_cli.schema import EmissionFactor
from carbon_cli.normalize import normalize_name
from typing import Optional, Tuple

BASE_SEARCH_URL = "https://nexus.openlca.org/search"

# Accept only units clearly matching kg/kg, kgCO2e/kg etc.
UNIT_WHITELIST = {
    "kg_co2e_per_kg",
    "kg/co2e/kg",
    "kgCO2e/kg",
    "kg_co2e per kg",
    "kg / kg",
    "kg/kg",
    "kg_co2e/kg",
}


def get_openlca_factor(substance: str) -> Tuple[Optional[EmissionFactor], str]:
    """
    Scrape OpenLCA Nexus for emission factor for normalized chemical name.
    Returns (EmissionFactor, debug_log) or (None, error_log).
    """
    try:
        s = httpx.Client(timeout=15)
        norm = normalize_name(substance)
        # Step 1: Search
        params = {"q": norm}
        r = s.get(BASE_SEARCH_URL, params=params)
        if r.status_code != 200:
            return None, f"OpenLCA HTTP error {r.status_code}: {r.text}"
        soup = BeautifulSoup(r.text, "html.parser")
        # Find candidate records (look for 'Life Cycle Inventory' or similar, take best match)
        cards = soup.select('a[href^="/record/"]')
        debug = []
        found_robust = None
        found_robust_log = None

        for card in cards:
            href = card.get("href")
            text = card.text.lower()
            debug.append(f"Found card: {text.strip()}")
            # Prefer records with 'inventory', 'manufacture', or exact/substring match
            preferred = any(
                x in text for x in [norm, "inventory", "manufacture", "production"]
            )
            detail_url = f"https://nexus.openlca.org{href}"
            r2 = s.get(detail_url)
            if r2.status_code != 200:
                debug.append(f"Failed to fetch details: {r2.status_code}")
                continue
            detail = BeautifulSoup(r2.text, "html.parser")
            factor, unit = None, None
            found_factor_row = None
            for row in detail.find_all("tr"):
                cols = [c.text.strip() for c in row.find_all("td")]
                s_row = " | ".join(cols)
                if len(cols) >= 2 and any(
                    u.replace(" ", "").lower() in cols[1].replace(" ", "").lower()
                    for u in UNIT_WHITELIST
                ):
                    try:
                        fval = float(cols[0])
                        uval = cols[1]
                        if preferred and not found_robust:
                            # Return first preferred match immediately
                            ef = EmissionFactor(
                                substance=norm,
                                factor=fval,
                                unit="kg_co2e_per_kg",
                                source="openlca",
                                source_url=detail_url,
                            )
                            return (
                                ef,
                                f"Preferred match (reason: '{text.strip()}'): {s_row}. {debug}",
                            )
                        # Keep first fallback for post-loop fallback
                        if not found_robust:
                            found_robust = EmissionFactor(
                                substance=norm,
                                factor=fval,
                                unit="kg_co2e_per_kg",
                                source="openlca",
                                source_url=detail_url,
                            )
                            found_robust_log = f"Fallback robust match from card '{text.strip()}': {s_row}"
                    except Exception as e:
                        debug.append(f"Failed parsing factor from: {s_row}: {e}")
            # ... keep looping to find possible preferred first, fallback after
        if found_robust:
            return found_robust, found_robust_log + f". Full scan info: {debug}"
        return None, f"OpenLCA: No usable match for '{norm}'. Debug: {debug}"
    except Exception as e:
        return None, f"OpenLCA: Error {e}"
