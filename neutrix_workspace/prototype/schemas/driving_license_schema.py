from pydantic import Field, validator
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
import re
from .base import BaseDocumentSchema

class DrivingLicenseSchema(BaseDocumentSchema):
    document_type: str = "driving_license"
    dl_number: str = Field(..., description="Driving License Number")
    name: Optional[str] = None
    father_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_issue: Optional[str] = None
    valid_till: Optional[str] = None
    issuing_authority: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    vehicle_classes: List[Dict[str, Any]] = Field(default_factory=list)
    national_validity: Optional[str] = None
    form_number: Optional[str] = None

    @validator('dl_number')
    def validate_dl_number(cls, v):
        # Basic validation for Indian DL format
        if not re.match(r"^[a-zA-Z0-9\s-]{5,20}$", v.strip()):
            pass # Be permissive for now to avoid dropping valid docs due to OCR missed spaces
        return v
