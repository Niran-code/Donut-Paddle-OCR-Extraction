from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class VoterIDSchema(BaseDocumentSchema):
    document_type: str = "Voter ID"
    name: Optional[str] = Field(None, description="Elector's Name")
    father_name: Optional[str] = Field(None, description="Father's/Husband's Name")
    dob: Optional[str] = Field(None, description="Date of birth")
    voter_id_number: str = Field(..., description="EPIC Number")
    gender: Optional[str] = Field(None, description="Gender: Male/Female")

    @validator('voter_id_number')
    def validate_voter_id_number(cls, v):
        if not re.match(r"^[A-Z]{3}[0-9]{7}$", v.replace(" ", "")):
            raise ValueError("Invalid Voter ID Number format (EPIC should be 3 letters + 7 digits)")
        return v
