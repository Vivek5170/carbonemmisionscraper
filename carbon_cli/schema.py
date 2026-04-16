from pydantic import BaseModel
from typing import Literal


class EmissionFactor(BaseModel):
    substance: str  # normalized chemical name queried
    factor: float  # numeric value (per kg)
    unit: Literal["kg_co2e_per_kg"] = "kg_co2e_per_kg"  # always normalized
    source: str  # e.g. 'climatiq', 'openlca', 'dataset'
    source_url: str  # URL to detailed record or dataset home page

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
