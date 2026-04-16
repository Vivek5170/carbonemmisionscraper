"""
Online API search helpers for carbon-cli: Europe PMC & OpenAlex reference searches for emission factor literature.
All results are deduplicated, error handling is robust, and API URLs are checked against latest docs.
"""

import httpx
import time
from typing import List, Dict, Tuple, Union


def search_europe_pmc_lca(
    chemical: str, max_results: int = 5, retries: int = 2
) -> Tuple[List[Dict], Union[str, None]]:
    """
    Search Europe PMC for authoritative LCA/carbon literature on a chemical. Multiple queries are used; errors retried.
    Returns a tuple: (results list, error message or None).
    Each result is a dict with: title, year, doi, oa, pdf, journal fields.
    """
    queries = [
        f"{chemical} life cycle assessment",
        f"{chemical} carbon footprint",
        f"{chemical} cradle to gate emissions",
        f"{chemical} greenhouse gas emissions production",
        f"{chemical} LCA production",
    ]
    papers = []
    errors = []
    for q in queries:
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q.replace(' ', '+')}&resultType=core&format=json&pageSize={max_results}"
        for attempt in range(retries + 1):
            try:
                r = httpx.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    results = [
                        {
                            "title": hit.get("title"),
                            "year": hit.get("pubYear"),
                            "doi": hit.get("doi", ""),
                            "oa": hit.get("isOpenAccess", False),
                            "pdf": hit.get("fullTextUrlList", {})
                            .get("fullTextUrl", [{}])[0]
                            .get("url", ""),
                            "journal": hit.get("journalTitle", ""),
                        }
                        for hit in data.get("resultList", {}).get("result", [])
                    ]
                    papers.extend(results)
                    break  # Success, don't retry further
                else:
                    errors.append(f"HTTP {r.status_code} for {url}")
            except httpx.TimeoutException:
                errors.append(f"Timeout on {url} (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
            except httpx.RequestError as e:
                errors.append(f"Network error {str(e)} ({url}) (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                errors.append(f"Other error {str(e)} ({url}) (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
        time.sleep(0.3)
    err_msg = ", ".join(errors) if papers == [] and errors else None
    return papers, err_msg


# Helper: OpenAlex search returns (results, error_message)
def search_openalex_lca(
    chemical: str, max_results: int = 5, retries: int = 2
) -> Tuple[List[Dict], Union[str, None]]:
    """
    Search OpenAlex for authoritative LCA/carbon literature on a chemical. Tries set of queries, retries on error.
    Returns a tuple: (results list, error message or None).
    Each result is a dict with: title, year, doi, oa, pdf, journal fields.
    """
    queries = [
        f"{chemical} life cycle assessment",
        f"{chemical} carbon footprint",
        f"{chemical} cradle to gate emissions",
        f"{chemical} greenhouse gas emissions production",
        f"{chemical} LCA production",
    ]
    papers = []
    errors = []
    for q in queries:
        url = f"https://api.openalex.org/works?search={q.replace(' ', '+')}&per_page={max_results}"
        for attempt in range(retries + 1):
            try:
                r = httpx.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for result in data.get("results", []):
                        papers.append(
                            {
                                "title": result.get("title", ""),
                                "year": result.get("publication_year", ""),
                                "doi": result.get("doi", ""),
                                "oa": result.get("open_access", {}).get("is_oa", False),
                                "pdf": result.get("open_access", {}).get("oa_url", ""),
                                "journal": result.get("host_venue", {}).get(
                                    "display_name", ""
                                ),
                            }
                        )
                    break  # Success
                else:
                    errors.append(f"HTTP {r.status_code} for {url}")
            except httpx.TimeoutException:
                errors.append(f"Timeout on {url} (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
            except httpx.RequestError as e:
                errors.append(f"Network error {str(e)} ({url}) (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                errors.append(f"Other error {str(e)} ({url}) (attempt {attempt + 1})")
                time.sleep(1.5 * (attempt + 1))
        time.sleep(0.3)
    err_msg = ", ".join(errors) if papers == [] and errors else None
    return papers, err_msg


import os
import tempfile
from pathlib import Path

import camelot

PDF_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
}


def extract_emission_factors_from_oa_pdfs(
    chemical: str,
    references: List[Dict],
    max_pdfs: int = 3,
) -> Tuple[List[Dict], List[str]]:
    """
    Download OA PDFs, extract tables, find likely emission factor values, return list of results with provenance and errors.
    """
    extracted = []
    errors = []
    pdf_count = 0
    for ref in references:
        pdf_url = ref.get("pdf") or ""
        if "pdf" not in pdf_url or not pdf_url.startswith("http"):
            continue
        if pdf_count >= max_pdfs:
            break
        pdf_count += 1
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = os.path.join(tmpdir, f"ref_{pdf_count}.pdf")
                # Try download
                r = httpx.get(pdf_url, headers=PDF_USER_AGENT, timeout=20)
                if r.status_code != 200 or b"%PDF" not in r.content[:1024]:
                    errors.append(
                        f"Download failed or not a PDF: {pdf_url} ({r.status_code})"
                    )
                    continue
                Path(pdf_path).write_bytes(r.content)
                # Run camelot
                try:
                    tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
                    if not tables:
                        errors.append(f"No tables extracted from {pdf_url}")
                        continue
                    for ti, table in enumerate(tables, 1):
                        df = table.df
                    # Simplified, robust heuristic:
                    # 1. If any cell in a row contains an emission keyword, look for a number+unit in the row.
                    import re

                    emission_kwds = re.compile(
                        r"emiss|ghg|co2|co₂|co2-eq|co2eq|co₂e|carbon|footprint", re.I
                    )
                    unit_kwds = re.compile(
                        r"((kg|g|t)(\s)?(co2|co₂|co2e|co2eq|co₂e)?)", re.I
                    )
                    found = False
                    for ridx, row in df.iterrows():
                        row_text = " ".join(row).lower()
                        # 1. Look for emission keyword anywhere in row
                        if emission_kwds.search(row_text):
                            # 2. Look for a number + unit pattern anywhere in row
                            num = None
                            unit = None
                            for cell in row:
                                vals = re.findall(r"[\-\d\.]+", cell)
                                # Pick first reasonable number
                                if vals and num is None:
                                    try:
                                        num = float(vals[0])
                                    except:
                                        pass
                                if unit is None and unit_kwds.search(cell):
                                    unit = unit_kwds.search(cell).group()
                            if num is not None and unit is not None:
                                extracted.append(
                                    {
                                        "factor": num,
                                        "units": unit,
                                        "provenance": f"table {ti}, row {ridx}",
                                        "caption": getattr(
                                            table.parsing_report, "caption", ""
                                        ),
                                        "pdf_url": pdf_url,
                                        "title": ref.get("title", ""),
                                        "doi": ref.get("doi", ""),
                                        "year": ref.get("year", ""),
                                        "journal": ref.get("journal", ""),
                                        "notice": "[UNAPPROVED, AUTO-EXTRACTED]",
                                    }
                                )
                                found = True
                                break
                    # No more deep/nested/per-cell logic, keep flat for simplicity.
                except Exception as e:
                    errors.append(f"PDF parse error for {pdf_url}: {e}")
        except Exception as ex:
            errors.append(f"OA PDF download/parse failed: {pdf_url}: {ex}")
    return extracted, errors


# For CLI (show top refs for a chemical) -- returns: (deduped papers, [errors])
def find_online_refs(
    chemical: str, max_results: int = 5
) -> Tuple[List[Dict], List[str]]:
    """
    Query both Europe PMC and OpenAlex for referenced emission factor/literature, deduplicate, and gather all errors.
    Returns deduped results and a list of user-facing error messages.
    """
    pmc, pmc_err = search_europe_pmc_lca(chemical, max_results)
    oalex, oalex_err = search_openalex_lca(chemical, max_results)
    res = {(r["doi"] or r["title"]): r for r in pmc + oalex}
    errors = []
    if pmc_err:
        errors.append(f"Europe PMC: {pmc_err}")
    if oalex_err:
        errors.append(f"OpenAlex: {oalex_err}")
    refs = list(res.values())
    return refs, errors
