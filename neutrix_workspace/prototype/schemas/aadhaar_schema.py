from pydantic import Field, validator, constr
from typing import Optional
import re
from .base import BaseDocumentSchema

class AadhaarSchema(BaseDocumentSchema):
    document_type: str = "Aadhaar Card"
    name: Optional[str] = Field(None, description="Name on Aadhaar")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or DD-MM-YYYY formats")
    gender: Optional[str] = Field(None, description="Gender: Male/Female")
    aadhaar_number: str = Field(..., description="12 digit Aadhaar number in XXXX XXXX XXXX format")

    @validator('aadhaar_number')
    def validate_aadhaar_number(cls, v):
        if not re.match(r"^\d{4}\s\d{4}\s\d{4}$", v):
            raise ValueError("Aadhaar number must be in XXXX XXXX XXXX format")
        return v
