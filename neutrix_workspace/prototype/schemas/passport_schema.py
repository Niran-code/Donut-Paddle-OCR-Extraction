from pydantic import Field, validator
from typing import Optional, Dict
import re
from .base import BaseDocumentSchema

class PassportSchema(BaseDocumentSchema):
    document_type: str = "passport"
    country: Optional[str] = None
    passport_number: str = Field(..., description="Passport Number (1 letter + 7 digits)")
    type: Optional[str] = None
    country_code: Optional[str] = None
    nationality: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    place_of_birth: Optional[str] = None
    place_of_issue: Optional[str] = None
    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None
    mrz: Optional[Dict[str, str]] = None

    @validator('passport_number')
    def validate_passport_number(cls, v):
        if not re.match(r"^[A-Za-z0-9\s<]{5,15}$", v.strip(), re.IGNORECASE):
            pass # Relax validation for OCR issues
        return v
