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


def get_dataset_factor(
    substance: str, csv_path: str
) -> Tuple[Optional[EmissionFactor], str]:
    """
    Search dataset for chemical name. Returns (EmissionFactor, debug_reason) if found, (None, error_msg) otherwise.
    """
    normalized = normalize_name(substance)
    checked_rows = []
    try:
        with open(csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                norm_row_name = normalize_name(row["substance"])
                row_unit = row["unit"].replace(" ", "").lower()
                checked_rows.append(
                    f"Tried '{row['substance']}' as '{norm_row_name}' with unit '{row['unit']}'"
                )
                if norm_row_name != normalized:
                    continue
                if row_unit not in {u.replace(" ", "").lower() for u in UNIT_WHITELIST}:
                    checked_rows.append(f"Rejected: Wrong unit '{row['unit']}'")
                    continue
                try:
                    factor = float(row["factor"])
                except Exception as e:
                    checked_rows.append(
                        f"Rejected: couldn't parse factor {row['factor']} ({e})"
                    )
                    continue
                ef = EmissionFactor(
                    substance=norm_row_name,
                    factor=factor,
                    unit="kg_co2e_per_kg",
                    source="dataset",
                    source_url=row.get("source_url") or "",
                )
                return (
                    ef,
                    f"Success: used dataset match '{row['substance']}'. Checks: {checked_rows}",
                )
    except FileNotFoundError:
        return None, f"Dataset file '{csv_path}' not found."
    except Exception as e:
        return None, f"Failed to read dataset: {e}"
    return None, f"No dataset match for '{normalized}'. Checked: {checked_rows}"
