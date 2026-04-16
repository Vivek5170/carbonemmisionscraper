"""
Carbon CLI Main Entrypoint. Handles CLI option parsing, dataset lookup, provenance auditing, grouping & online search.
"""

import os
import typer
from rich.console import Console
from rich.table import Table
from carbon_cli.normalize import normalize_name
from carbon_cli.sources import dataset
from carbon_cli.utils import grams_to_kg
from carbon_cli.schema import EmissionFactor
from carbon_cli.pubchem import get_pubchem_synonyms


app = typer.Typer()
console = Console()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "data", "emission_factors.csv")


def show_online_refs(substance: str, dur: float) -> None:
    """Query Europe PMC and OpenAlex for referenced emission factors/literature and print results and error messages consistently."""
    print(
        "\n[INFO] Searching online for referenced emission factor literature (Europe PMC, OpenAlex)..."
    )
    from carbon_cli.sources.find_online import find_online_refs

    papers, errors = find_online_refs(substance, max_results=5)
    if errors:
        print("[ERROR] Issue(s) encountered while querying online references:")
        for err in errors:
            print(f"    {err}")
        print(
            "[INFO] Online reference database(s) may be temporarily unreachable or blocked. Please check your internet connection or try again later."
        )
    if not papers:
        print(
            "[INFO] No referenced OA papers found with possible emission factors for this chemical."
        )
    else:
        print(
            f"[INFO] Found {len(papers)} referenced publications (deduped by DOI/title):\n"
        )
        for i, paper in enumerate(papers, 1):
            print(
                f"[{i}] {paper.get('title', '').strip()}\n    Year: {paper.get('year', '')}\n    DOI: {paper.get('doi', '')}\n    Journal: {paper.get('journal', '')}\n    OA PDF: {paper.get('pdf', '')}"
            )
        # Try extracting emission factors from OA PDFs
        from carbon_cli.sources.find_online import extract_emission_factors_from_oa_pdfs

        oa_factors, oa_errors = extract_emission_factors_from_oa_pdfs(substance, papers)
        if oa_errors:
            print("[AUTO EXTRACTION ERRORS]")
            for err in oa_errors:
                print(f"    {err}")
        if oa_factors:
            print("[AUTO-EXTRACTED EMISSION FACTORS FROM OA PDFs] (UNAPPROVED)")
            from rich.table import Table

            t = Table(
                title="Extracted Emission Factors from OA Literature (UNAPPROVED)"
            )
            t.add_column("Value")
            t.add_column("Units/Context")
            t.add_column("Provenance (table/row/col)")
            t.add_column("Paper")
            for rec in oa_factors:
                # Unit normalization attempt
                val = rec.get("factor")
                unit = rec.get("units", "")
                from carbon_cli.utils import normalize_unit_and_value

                try:
                    total, unit_out = normalize_unit_and_value(val, unit, weight_g)
                    est_row = f"{total:.6g} {unit_out} (input = {weight_g}g)"
                except Exception as ex:
                    est_row = f"Failed: {ex}"
                t.add_row(
                    str(rec.get("factor")),
                    rec.get("units", ""),
                    rec.get("provenance", ""),
                    f"{rec.get('title', '')[:40]}...\nDOI:{rec.get('doi', '')} PDF:{rec.get('pdf_url', '')}",
                )
                t.add_row("Estimated Total Carbon (auto, unapproved)", est_row)
            from rich.console import Console

            console = Console()
            console.print(t)
        else:
            print(
                "[INFO] No emission factor tables detected in OA PDFs for this search (best effort)."
            )


# Util for describing result from each source
class SourceAttempt:
    """Tracks results for each data source check (with reason if no match)."""

    def __init__(self, name: str):
        self.name = name
        self.result = None  # type: EmissionFactor or None
        self.reason = None  # str

    def record(self, result, reason: str):
        self.result = result
        self.reason = reason


def print_result(
    queried: str, norm: str, weight_g: float, attempts: list, used_idx: int = None
) -> None:
    """
    Render the computed carbon result in a pretty table (Rich), showing input, all sources checked, outcome, and full provenance.
    Used index is highlighted if a successful match is chosen.
    """
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
        table.add_section()
        table.add_row("CAS Number", getattr(ef, "cas_number", ""))
        table.add_row("Formula", getattr(ef, "formula", ""))
        table.add_row("Synonyms", getattr(ef, "synonyms", ""))
        table.add_row("Emission Factor (kg/kg)", str(ef.factor))
        table.add_row("Process", getattr(ef, "process", "unknown"))
        table.add_row("Boundary", getattr(ef, "boundary", ""))
        table.add_row("Year", getattr(ef, "year", ""))
        table.add_row("Normalized per gram", f"{per_gram:.6g} kg_co2e/g")
        table.add_row("Confidence", ef.confidence)
        table.add_row("Reference Link", ef.reference_url)
        table.add_row("DOI", ef.doi)
        table.add_row("Page", getattr(ef, "page_number", ""))
        table.add_row("Table ID", getattr(ef, "table_id", ""))
        table.add_row("Caption", getattr(ef, "caption", ""))
        table.add_row("Extraction Method", getattr(ef, "extraction_method", ""))
        table.add_row("Source (description)", ef.source)
        table.add_row("Total Carbon Footprint (kg CO2e)", f"{kg_footprint:.6g}")
    else:
        table.add_row("Result", "No emission factor found from any source.")
    console.print(table)


@app.command()
def main(
    substance: str = typer.Argument(None, help="Chemical substance name"),
    weight_g: float = typer.Argument(None, help="Mass in grams"),
    find_online: bool = typer.Option(
        False,
        "--find-online",
        help="If no local result, live-query referenced API sources (Europe PMC, OpenAlex) for recent literature on emission factors.",
    ),
):
    """Estimate embedded carbon from chemical manufacture.

    This command normalizes your chemical identifier, aggregates all referenced emission factor records from the
    local dataset, groups by provenance (CAS, process, boundary), and provides all grouping statistics/reporting.
    With --find-online, it will also search referenced open literature APIs for the queried chemical.
    """
    # Interactive fallback
    if not substance:
        substance = typer.prompt("Enter the chemical substance name")
    if not weight_g:
        weight_g = float(typer.prompt("Enter mass in grams"))
    norm = normalize_name(substance)
    synonyms = get_pubchem_synonyms(substance)
    # Ensure original chemical name is first. Normalize all and keep only up to 10 unique synonyms.
    main_name = normalize_name(substance)
    synonyms = list(
        dict.fromkeys(
            [main_name]
            + [normalize_name(s) for s in synonyms if normalize_name(s) != main_name]
        )
    )[:10]
    attempts = [SourceAttempt("Dataset CSV")]
    # main uses: time for profiling, statistics for group summary
    import time
    import statistics  # noqa: F401

    start = time.time()
    # Gather all emission factors for all synonyms (aggregate results!)
    all_results = []
    for s in synonyms:
        all_results.extend(dataset.get_all_dataset_factors(s, DATASET_PATH))
    dur = time.time() - start
    if all_results:
        # Group by (cas_number, process, boundary)
        from collections import defaultdict

        grouped = defaultdict(list)
        for ef in all_results:
            key = (ef.cas_number, ef.process, ef.boundary)
            grouped[key].append(ef)

        console.print(
            f"\n[INFO] Found {len(all_results)} referenced emission factor records for '{substance}' ({len(grouped)} groups).\n"
        )
        # Emit result table for each group
        for group_idx, (key, group) in enumerate(grouped.items(), 1):
            factors = [ef.factor for ef in group]
            med = statistics.median(factors)
            minv = min(factors)
            maxv = max(factors)
            count = len(factors)
            try:
                stddev = statistics.stdev(factors) if count > 1 else 0.0
            except Exception:
                stddev = 0.0
            console.rule(
                f"Group {group_idx}: CAS={key[0]}, Process={key[1]}, Boundary={key[2]}"
            )
            t = Table(title="Grouped Carbon Footprint Stats & Provenance")
            t.add_column("Stat/Provenance")
            t.add_column("Value", overflow="fold")
            t.add_row("N Records", str(count))
            t.add_row("Median", f"{med:.3g}")
            t.add_row("Min", f"{minv:.3g}")
            t.add_row("Max", f"{maxv:.3g}")
            t.add_row("StdDev", f"{stddev:.3g}")
            t.add_row("All Values", ", ".join(f"{v:.3g}" for v in factors))
            # Calculate and display total carbon for each record, with no approval/confidence distinction.
            t.add_section()
            for i, ef in enumerate(group, 1):
                from carbon_cli.utils import normalize_unit_and_value

                total, unit_out = normalize_unit_and_value(
                    ef.factor,
                    getattr(ef, "unit", ef.extraction_method or "kg"),
                    weight_g,
                )
                t.add_row(f"Record {i}", ef.reference_url or ef.doi or ef.source)
                t.add_row("Factor", str(ef.factor))
                t.add_row("Process", ef.process)
                t.add_row("Boundary", ef.boundary)
                t.add_row("Year", str(ef.year))
                t.add_row("Caption", str(ef.caption))
                t.add_row("Page/Table", f"{ef.page_number}/{ef.table_id}")
                t.add_row("Extraction", ef.extraction_method or "dataset")
                t.add_row(
                    "Estimated Total Carbon (auto)",
                    f"{total:.6g} {unit_out} (input = {weight_g}g)",
                )
                t.add_section()
            console.print(t)
        print(
            f"[INFO] Grouping/stats computation took {dur:.2f}s. Displaying all provenance and calculations."
        )
        raise typer.Exit()
    else:
        # Always try OA/online, cache via utils.cache
        if find_online:
            from carbon_cli.utils.cache import cache_lookup

            def oa_loader():
                from carbon_cli.sources.find_online import (
                    find_online_refs,
                    extract_emission_factors_from_oa_pdfs,
                )

                papers, errors = find_online_refs(substance, max_results=5)
                oa_factors, oa_errors = extract_emission_factors_from_oa_pdfs(
                    substance, papers
                )
                return (papers, errors, oa_factors, oa_errors)

            key = f"{substance.lower()}"
            (papers, errors, oa_factors, oa_errors), _ = cache_lookup(key, oa_loader)
            if errors:
                print("[ERROR] Issue(s) encountered while querying online references:")
                for err in errors:
                    print(f"    {err}")
            if papers:
                print(
                    f"[INFO] Found {len(papers)} referenced publications (deduped by DOI/title):\n"
                )
            if oa_errors:
                print("[AUTO EXTRACTION ERRORS]")
                for err in oa_errors:
                    print(f"    {err}")
            if oa_factors:
                print("[AUTO-EXTRACTED EMISSION FACTORS FROM OA PDFs] (UNAPPROVED)")
                from rich.table import Table

                t = Table(
                    title="Extracted Emission Factors from OA Literature (UNAPPROVED)"
                )
                t.add_column("Value")
                t.add_column("Units/Context")
                t.add_column("Provenance (table/row/col)")
                t.add_column("Paper")
                for rec in oa_factors:
                    val = rec.get("factor")
                    unit = rec.get("units", "")
                    from carbon_cli.utils import normalize_unit_and_value

                    try:
                        total, unit_out = normalize_unit_and_value(val, unit, weight_g)
                        est_row = f"{total:.6g} {unit_out} (input = {weight_g}g)"
                    except Exception as ex:
                        est_row = f"Failed: {ex}"
                    t.add_row(
                        str(rec.get("factor")),
                        rec.get("units", ""),
                        rec.get("provenance", ""),
                        f"{rec.get('title', '')[:40]}...\nDOI:{rec.get('doi', '')} PDF:{rec.get('pdf_url', '')}",
                    )
                    t.add_row("Estimated Total Carbon (auto, unapproved)", est_row)
                from rich.console import Console

                console = Console()
                console.print(t)
            else:
                print(
                    "[INFO] No emission factor tables detected in OA PDFs for this search (best effort)."
                )
        else:
            print(
                f"Dataset: {dur:.2f}s. Online sources not queried. Add --find-online to live-search referenced API sources."
            )

    # Moved this entire block up, use only one instance after main group/aggregation/online logic.
    # All emission factor found/aggregation/online search handled in the first block.
    pass  # This block has been deduplicated and is now unreachable; safe to remove.


if __name__ == "__main__":
    app()
