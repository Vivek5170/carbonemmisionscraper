import os
import httpx
from typing import Optional, Tuple
from carbon_cli.schema import EmissionFactor
from carbon_cli.normalize import normalize_name

API_BASE_URL = "https://api.climatiq.io/data/v1/search"
DATA_VERSION = "^2024"  # Use current or fallback version, update as needed

# Allowed unit variants corresponding to 'kg_co2e_per_kg'
UNIT_WHITELIST = {
    "kg_co2e/kg",
    "kg/co2e/kg",
    "kgCO2e/kg",
    "kg_co2e per kg",
    "kg / kg",
    "kg/kg",
    "kg_co2e_per_kg",
}  # extend as needed


def get_climatiq_factor(substance: str) -> Tuple[Optional[EmissionFactor], str]:
    """
    Query Climatiq API. Returns (EmissionFactor, debug_reason) if factor found, (None, error) if not/failure.
    Always normalizes units and checks debug errors per requirements.
    """
    normalized = normalize_name(substance)
    api_key = os.getenv("CLIMATIQ_API_KEY")
    if not api_key:
        return None, "Climatiq API key not found in CLIMATIQ_API_KEY env var."

    # Build request
    params = {"query": normalized, "data_version": DATA_VERSION, "results_per_page": 10}
    headers = {"Authorization": f"Bearer {api_key}"}
    debug_steps = []
    try:
        resp = httpx.get(API_BASE_URL, params=params, headers=headers, timeout=10)
        if resp.status_code == 401:
            return None, "Climatiq: Unauthorized (401). Check your API key."
        if resp.status_code != 200:
            return None, f"Climatiq error: HTTP {resp.status_code}: {resp.text}"
        data = resp.json()
    except Exception as e:
        return None, f"Climatiq request failed: {e}"

    for entry in data.get("results", []):
        # Unit check/normalization
        unit = entry.get("unit", "").replace(" ", "").lower().replace("co2e", "co2e")
        debug_steps.append(
            f"Result '{entry.get('name', '?')}', unit='{entry.get('unit', '')}'"
        )
        if not entry.get("factor"):
            debug_steps.append(f"Rejected result (No factor value available)")
            continue
        # Accept best matching unit
        if any(u.replace(" ", "").lower() == unit for u in UNIT_WHITELIST):
            factor = float(entry["factor"])
            ef = EmissionFactor(
                substance=normalized,
                factor=factor,
                unit="kg_co2e_per_kg",
                source="climatiq",
                source_url=entry.get("source_link") or "https://climatiq.io/data",
            )
            return (
                ef,
                f"Success, used entry with unit '{entry.get('unit', '')}'. {debug_steps}",
            )
        debug_steps.append("Rejected due to unsupported unit.")
    if len(data.get("results", [])) == 0:
        return None, f"Climatiq: No results for '{normalized}'. {debug_steps}"
    return (
        None,
        f"Climatiq: No matching emission factor in kg/kg or convertible unit for '{normalized}'. Details: {debug_steps}",
    )
