import typer
from rich.console import Console
from rich.table import Table
from carbon_cli.normalize import normalize_name
from carbon_cli.sources import climatiq, openlca, dataset
from carbon_cli.utils import grams_to_kg
from carbon_cli.schema import EmissionFactor
import os

app = typer.Typer()
console = Console()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "data", "emission_factors.csv")


# Util for describing result from each source
class SourceAttempt:
    def __init__(self, name):
        self.name = name
        self.result = None  # type: EmissionFactor or None
        self.reason = None  # str

    def record(self, result, reason):
        self.result = result
        self.reason = reason


def print_result(
    queried: str, norm: str, weight_g: float, attempts: list, used_idx: int = None
):
    table = Table(title="Carbon Footprint Calculation Result")
    table.add_column("Field")
    table.add_column("Value", overflow="fold")
    table.add_row("Substance Queried", queried)
    table.add_row("Normalized Name", norm)
    table.add_row("Weight (g)", str(weight_g))
    table.add_row("Weight (kg)", f"{grams_to_kg(weight_g):.6f}")

    table.add_section()
    table.add_row("Sources Checked", ", ".join([a.name for a in attempts]))
    for i, a in enumerate(attempts):
        val = "Success" if a.result else f"No match: {a.reason}"
        if used_idx is not None and i == used_idx:
            val += " [USED]"
        table.add_row(f"{a.name} result", val)

    if used_idx is not None:
        ef: EmissionFactor = attempts[used_idx].result
        per_gram = ef.factor / 1000
        kg_footprint = weight_g * per_gram
        table.add_row("Emission Factor (kg/kg)", str(ef.factor))
        table.add_row("Normalized per gram", f"{per_gram:.6g} kg_co2e/g")
        table.add_row("Source URL", ef.source_url)
        table.add_row("Total Carbon Footprint (kg CO2e)", f"{kg_footprint:.6g}")
    else:
        table.add_row("Result", "No emission factor found from any source.")
    console.print(table)


@app.command()
def main(
    substance: str = typer.Argument(None, help="Chemical substance name"),
    weight_g: float = typer.Argument(None, help="Mass in grams"),
):
    """Estimate embedded carbon from chemical manufacture."""
    # Interactive fallback
    if not substance:
        substance = typer.prompt("Enter the chemical substance name")
    if not weight_g:
        weight_g = float(typer.prompt("Enter mass in grams"))
    norm = normalize_name(substance)
    attempts = [
        SourceAttempt("Climatiq API"),
        SourceAttempt("OpenLCA Nexus"),
        SourceAttempt("Dataset CSV"),
    ]
    # Try sources in order
    ef, reason = climatiq.get_climatiq_factor(norm)
    attempts[0].record(ef, reason)
    if ef:
        print_result(substance, norm, weight_g, attempts, 0)
        raise typer.Exit()
    ef, reason = openlca.get_openlca_factor(norm)
    attempts[1].record(ef, reason)
    if ef:
        print_result(substance, norm, weight_g, attempts, 1)
        raise typer.Exit()
    ef, reason = dataset.get_dataset_factor(norm, DATASET_PATH)
    attempts[2].record(ef, reason)
    if ef:
        print_result(substance, norm, weight_g, attempts, 2)
        raise typer.Exit()
    print_result(substance, norm, weight_g, attempts, None)


if __name__ == "__main__":
    app()
