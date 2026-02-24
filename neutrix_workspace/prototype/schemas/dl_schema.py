from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class DLSchema(BaseDocumentSchema):
    document_type: str = "Driving License"
    name: Optional[str] = Field(None, description="Name on DL")
    dob: Optional[str] = Field(None, description="Date of birth")
    dl_number: str = Field(..., description="Driving License Number")
    issue_date: Optional[str] = None
    valid_till: Optional[str] = None
    address: Optional[str] = None

    @validator('dl_number')
    def validate_dl_number(cls, v):
        if not re.match(r"^[A-Z]{2}[0-9]{2,14}$", v.replace(" ", "").replace("-", "")):
            raise ValueError("Invalid Driving License Number format")
        return v
