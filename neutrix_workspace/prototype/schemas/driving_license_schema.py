from pydantic import Field, validator
from typing import Optional, List
import re
from .base import BaseDocumentSchema

class DrivingLicenseSchema(BaseDocumentSchema):
    document_type: str = "driving_license"
    dl_number: str = Field(..., description="Driving License Number")
    full_name: Optional[str] = None
    father_or_husband_name: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="Normalized YYYY-MM-DD")
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuing_authority: Optional[str] = None
    address: Optional[str] = None
    vehicle_classes: List[str] = Field(default_factory=list)

    @validator('dl_number')
    def validate_dl_number(cls, v):
        # Basic validation for Indian DL format (e.g. RJ14 20180000000)
        # Assuming permissive regex because formats vary slightly by state
        if not re.match(r"^[A-Z]{2}[0-9\s-]{1,18}$", v.strip()):
            raise ValueError("Invalid Driving License Number format")
        return v
