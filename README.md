# Carbon CLI

**Estimate the cradle-to-gate CO₂e emissions for chemicals using only best-available, referenced data sources.**

## ⚡ Quick Start
Install dependencies (recommended: `uv`, works with pip/poetry too):
```bash
uv venv
uv pip install -e .
```

**Run via CLI:**
```bash
carbon-cli "CHEMICAL NAME" MASS_IN_GRAMS
# Or just:
carbon-cli
# ...to run interactively (it will prompt you)
```
Or, if the above entrypoint isn't installed:
```bash
python -m carbon_cli "CHEMICAL NAME" MASS_IN_GRAMS
```

## Features
- Uses only open-access, highly referenced LCA data or published industry factors—NO estimates, no unverifiable values.
- All output includes complete provenance (source, DOI/URL, year, process, boundary, table if available).
- Fast, minimal dependencies. Cross-platform (uses `pathlib`).
- Built-in PDF/online extraction (if Ghostscript/Poppler/Camelot installed).

## Adding/Updating Data
1. Only add a value if it has a clear, open-access source (government LCA db, peer-reviewed paper, or industry PDF with citation).
2. Add a new row to `carbon_cli/data/emission_factors.csv`.
   - See the file for schema (substance, factor/unit/process/source/year/URL/DOI/...)
3. DO NOT add unverifiable values.
   - If you can’t find a value, leave the dataset empty or clearly note `no open, citable value available` in the CSV.

## PDF Table Extraction (Windows requirements)
- If you want PDF table scraping (OA extraction), you **must** install:
  - [Ghostscript](https://www.ghostscript.com/download/gsdnld.html)
  - [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
  - Add both to your PATH.
- For full directions see the [Camelot install guide](https://camelot-py.readthedocs.io/en/master/user/install-deps.html#windows).

## Troubleshooting
- Problems running? Make sure your environment is activated and dependencies installed (see above).
- PDF extraction errors? Double-check that Ghostscript and Poppler are installed & in your PATH on Windows.
- Only minimal dependencies used (see `pyproject.toml/requirements.txt`).

## License
MIT

---
**No sodium chloride emission factors available:** As of this release, no open, citable cradle-to-gate value was found in any global government or open LCA database; the local dataset is empty until such a value is located.
