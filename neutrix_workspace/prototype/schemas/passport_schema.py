from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class PassportSchema(BaseDocumentSchema):
    document_type: str = "passport"
    passport_number: str = Field(..., description="Passport Number (1 letter + 7 digits)")
    surname: Optional[str] = None
    given_names: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    place_of_birth: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    mrz_line1: Optional[str] = None
    mrz_line2: Optional[str] = None

    @validator('passport_number')
    def validate_passport_number(cls, v):
        if not re.match(r"^[A-Za-z][0-9]{7}$", v.strip(), re.IGNORECASE):
            raise ValueError("Invalid Passport Number format")
        return v
