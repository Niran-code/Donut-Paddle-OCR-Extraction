from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class PANSchema(BaseDocumentSchema):
    document_type: str = "PAN Card"
    name: Optional[str] = Field(None, description="Name on PAN")
    father_name: Optional[str] = Field(None, description="Father's name on PAN")
    dob: Optional[str] = Field(None, description="Date of birth")
    pan_number: str = Field(..., description="10 character PAN number")

    @validator('pan_number')
    def validate_pan_number(cls, v):
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", v):
            raise ValueError("PAN number must be 5 letters, 4 numbers, 1 letter")
        return v
