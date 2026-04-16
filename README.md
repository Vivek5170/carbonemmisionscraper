# Carbon CLI

**Estimate cradle-to-gate CO₂e emissions for chemicals using only the best-available, referenced data sources.**

---

## ⚡ Quick Start

### 1. Create and activate a virtual environment

#### Recommended (fastest):
```bash
uv venv
source .venv/bin/activate
```
#### Or, using standard Python tools:
```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
.venv\Scripts\activate    # On Windows
```

### 2. Install dependencies and the CLI package

```bash
uv pip install -e .           # or:
pip install -e .
```

### 3. Run the CLI

```bash
carbon-cli "CHEMICAL NAME" MASS_IN_GRAMS
# Example (will show no result if no verified data):
carbon-cli "sodium chloride" 1000

# Or search open-access literature for factors (Europe PMC, OpenAlex, etc):
carbon-cli "sodium chloride" 1000 --find-online

# Or interactively (with prompts for options):
carbon-cli
```

If `carbon-cli` is not found (entrypoint not active), use:
```bash
python -m carbon_cli "CHEMICAL NAME" MASS_IN_GRAMS
python -m carbon_cli "sodium chloride" 1000 --find-online
```
# (Both CLI and module accept --find-online)

---

## Confirmation/Test

Verify installation with:
- `carbon-cli --help`
- `python -m carbon_cli --help`

Both should display usage/help. If not, check your environment activation and install step.

---

## Features
- Uses only open-access, high-quality LCA data or published industry factors—**NO unverifiable values.**
- All queries return complete provenance (source, DOI/URL, year, process, boundary, table, etc.).
- Fast, minimal, modern dependencies. Fully cross-platform (uses pathlib, Typer, etc.).
- Built-in PDF extraction (if Ghostscript, Poppler, Camelot are installed).
- Optionally live-queries open literature databases (Europe PMC, OpenAlex) for up-to-date emission factors when you add `--find-online`.

---

## Adding or Updating Emission Factor Data
- **Only add a value with an open-access source** (gov LCA db, peer-reviewed paper, or cited industry PDF).
- Add one row per value to `carbon_cli/data/emission_factors.csv`.
  - See the file for required columns (substance, factor, unit, process, source, year, URL, DOI, etc.).
- **Never add unverifiable or uncited numbers.**
- If no open, citable value is available, leave the dataset empty **or** enter a line clearly stating `no open, citable value available` as a comment (with `#`).

---

## PDF Table Extraction (Windows requirements)
If you need PDF table extraction ("OA extraction"), install:
- [Ghostscript](https://www.ghostscript.com/download/gsdnld.html)
- [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
- Add both to your PATH

See full directions in the [Camelot install guide](https://camelot-py.readthedocs.io/en/master/user/install-deps.html#windows).

---

## Troubleshooting
- **Command not found?** Ensure `.venv/bin` (or `.venv\Scripts` on Windows) is in your `PATH` and the venv is activated.
- **PDF extraction errors?** Make sure Ghostscript and Poppler are installed and in your PATH (Windows only).
- Only minimal dependencies used (see `pyproject.toml`).

---

## License
MIT

---

**Current data status:** _As of this release, no open, citable cradle-to-gate emission factor exists for sodium chloride in any public LCA or open database; the local CSV dataset is intentionally left empty._

