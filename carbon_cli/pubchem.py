# PubChem utility for chemical identifier/synonym/CAS lookup
import httpx
from typing import List, Dict, Optional

PUG_VIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"


def get_pubchem_synonyms(name: str) -> List[str]:
    """
    Given a chemical name, return a list of synonyms (from PubChem REST API)
    Returns at least the original name. On error, returns [name].
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/synonyms/TXT"
    try:
        resp = httpx.get(url, timeout=5)
        if resp.status_code != 200:
            return [name]
        syns = resp.text.strip().split("\n")
        return sorted(set([s.strip() for s in syns if s.strip()]))
    except Exception:
        return [name]


def get_pubchem_cids(name: str) -> List[int]:
    """
    Lookup PubChem Compound IDs for a substance name/identifier.
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/TXT"
    try:
        resp = httpx.get(url, timeout=5)
        if resp.status_code != 200:
            return []
        return [int(line) for line in resp.text.strip().split("\n") if line.isdigit()]
    except Exception:
        return []


def get_pubchem_identifiers(name: str) -> Optional[Dict[str, str]]:
    """
    Given a chemical name, attempts to resolve:
      - CAS number
      - formula
      - preferred synonyms
    Returns a dict or None.
    """
    cids = get_pubchem_cids(name)
    if not cids:
        return None
    # Use first CID
    cid = cids[0]
    url = PUG_VIEW_URL.format(cid=cid)
    try:
        resp = httpx.get(url, timeout=7)
        if resp.status_code != 200:
            return None
        data = resp.json()
        out = {"cas_number": "", "formula": "", "synonyms": []}
        for sec in data.get("Record", {}).get("Section", []):
            if sec.get("TOCHeading") == "Names and Identifiers":
                for ele in sec.get("Section", []):
                    if ele.get("TOCHeading") == "CAS":
                        vals = ele.get("Information", [])
                        if vals and "Value" in vals[0]:
                            cas_l = vals[0]["Value"].get("StringWithMarkup")
                            if cas_l:
                                out["cas_number"] = cas_l[0]["String"]
                    if ele.get("TOCHeading") == "Molecular Formula":
                        vals = ele.get("Information", [])
                        if vals and "Value" in vals[0]:
                            mf_l = vals[0]["Value"].get("StringWithMarkup")
                            if mf_l:
                                out["formula"] = mf_l[0]["String"]
                    if ele.get("TOCHeading") == "Synonyms":
                        vals = ele.get("Information", [])
                        if vals and "Value" in vals[0]:
                            syns = vals[0]["Value"].get("StringWithMarkup", [])
                            out["synonyms"] = [s["String"] for s in syns if s["String"]]
        return out
    except Exception:
        return None
