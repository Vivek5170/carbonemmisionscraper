from pydantic import BaseModel
from typing import Literal


class EmissionFactor(BaseModel):
    substance: str  # normalized chemical name queried
    cas_number: str = ""  # CAS registry number
    formula: str = ""  # Chemical formula
    synonyms: str = ""  # Comma- or semicolon-separated list of synonyms
    factor: float  # numeric value (per kg)
    unit: Literal["kg_co2e_per_kg"] = "kg_co2e_per_kg"  # always normalized
    process: str = "unknown"  # production route or process (optional)
    boundary: str = "unknown"  # System boundary (cradle-to-gate, cradle-to-grave, etc.)
    source: str  # journal/report/publisher
    year: str = ""
    confidence: str = "unknown"  # high/medium/low
    reference_url: str = ""  # Source dataset reference, DOI, or paper/page
    doi: str = ""  # Digital Object Identifier or empty
    page_number: str = ""  # page in PDF
    table_id: str = ""  # Table 2, Table S3, etc.
    caption: str = ""  # Table or figure caption text
    extraction_method: str = ""  # 'pdf_table', 'html_table', etc.

    class Config:
        json_schema_extra = {
            "example": {
                "substance": "sodium azide",
                "factor": 7.5,
                "unit": "kg_co2e_per_kg",
                "source": "climatiq",
                "source_url": "https://api.climatiq.io/record/1234",
            }
        }
