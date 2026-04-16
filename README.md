# carbon-cli

Estimate embedded CO₂e from chemical manufacturing, with CLI, robust source fallback, and normalization.

## Features
- **CLI Usage:**
  - Command line: `carbon-cli "sodium azide" 50`
  - If arguments are missing: prompts interactively

- **Sources (in order):**
  1. **Climatiq API** (`https://api.climatiq.io`) – Requires a paid API key in env var `CLIMATIQ_API_KEY`. Community/free plans may return no factors.
  2. **OpenLCA Nexus Web Scraper** (`https://nexus.openlca.org`) – Web scrapes the Nexus data portal for life cycle inventory emission factors for chemicals.
  3. **Local Dataset** (`data/emission_factors.csv`) – Always works as fallback/demo.

- **Normalization:**
  - Substance names are normalized (case, hyphens, whitespace)
  - Emission factors converted and used only if \*per kg\* (i.e., `kg_co2e_per_kg` or equivalent)

- **Output:**
  - Rich, structured table,
  - Shows which sources succeeded/failed and why
  - Calculation for the given mass in g and kg

- **Dependencies:**
  - uv, typer, rich, pydantic, httpx, beautifulsoup4

## Installation & Setup

```bash
uv venv                # Create a virtual environment
uv pip install -e .    # Install all dependencies in development mode
export CLIMATIQ_API_KEY=YOUR_API_KEY   # Optional: For Climatiq API source
```

## Usage
```bash
python -m carbon_cli "CHEMICAL NAME" MASS_IN_GRAMS

# Or, interactive mode:
python -m carbon_cli
```

## File Structure
```
carbon_cli/
  __main__.py        # CLI/Entrypoint
  normalize.py       # Name normalization helpers
  utils.py           # Misc utilities
  schema.py          # EmissionFactor schema
  sources/
    climatiq.py      # Calls Climatiq API
    openlca.py       # Scrapes OpenLCA Nexus
    dataset.py       # Loads local CSV fallback dataset
  data/
    emission_factors.csv  # Demo fallback chemical factors
```

## Troubleshooting
- **Climatiq always fails with 'No factor' or 401?** Community plan doesn't expose factor. Use paid account or rely on other sources.
- **OpenLCA returns 'not implemented'?** Update to latest or check that dependencies are installed. (This repo includes scraping logic.)
- **CLI doesn't work?** Make sure dependencies in the above list are installed _inside_ your virtual environment.

## License
MIT

---
## Developer Notes
- Implements strict normalization and source chain per requirements.
- To add new factors, edit `data/emission_factors.csv`.

---
### Why OpenLCA May Not Work
- OpenLCA uses web-based data, does not have a public API, and can be slow or change structure. Scraping logic must be robust to changes in the HTML. If scraping fails, a transparent error explains why and shows checked sources.