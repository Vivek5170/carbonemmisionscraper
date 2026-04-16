# Chemical name normalization helpers
import re


def normalize_name(name: str) -> str:
    """
    Lowercase, remove hyphens, condense whitespace, standardize names like 'NaN3'/'sodium-azide'.
    """
    name = name.lower().replace("-", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()
