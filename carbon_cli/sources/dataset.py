import csv
from typing import Optional, Tuple
from carbon_cli.schema import EmissionFactor
from carbon_cli.normalize import normalize_name

UNIT_WHITELIST = {
    "kg_co2e_per_kg",
    "kg/co2e/kg",
    "kgCO2e/kg",
    "kg_co2e per kg",
    "kg / kg",
    "kg/kg",
    "kg_co2e/kg",
}


def get_all_dataset_factors(substance: str, csv_path: str):
    """
    Return a list of all EmissionFactor matches (case-insensitive, normalized).
    """
    normalized = normalize_name(substance)
    results = []
    try:
        with open(csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                norm_row_name = normalize_name(row["substance"])
                row_unit = row["unit"].replace(" ", "").lower()
                if norm_row_name != normalized:
                    continue
                if row_unit not in {u.replace(" ", "").lower() for u in UNIT_WHITELIST}:
                    continue
                try:
                    factor = float(row["factor"])
                except Exception:
                    continue
                ef = EmissionFactor(
                    substance=norm_row_name,
                    cas_number=row.get("cas_number") or "",
                    formula=row.get("formula") or "",
                    synonyms=row.get("synonyms") or "",
                    factor=factor,
                    unit=row.get("unit") or "kg_co2e_per_kg",
                    process=row.get("process") or "unknown",
                    boundary=row.get("boundary") or "unknown",
                    source=row.get("source") or "",
                    year=row.get("year") or "",
                    confidence=row.get("confidence") or "unknown",
                    reference_url=row.get("reference_url") or "",
                    doi=row.get("doi") or "",
                    page_number=row.get("page_number") or "",
                    table_id=row.get("table_id") or "",
                    caption=row.get("caption") or "",
                    extraction_method=row.get("extraction_method") or "",
                )
                results.append(ef)
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return results
