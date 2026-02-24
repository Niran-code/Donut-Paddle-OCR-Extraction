from .base import BaseDocumentSchema
from .aadhaar_schema import AadhaarSchema
from .pan_schema import PANSchema
from .dl_schema import DLSchema
from .driving_license_schema import DrivingLicenseSchema
from .passport_schema import PassportSchema
from .marksheet_schema import MarksheetSchema
from .voter_id_schema import VoterIDSchema

__all__ = [
    "BaseDocumentSchema",
    "AadhaarSchema",
    "PANSchema",
    "DLSchema",
    "DrivingLicenseSchema",
    "PassportSchema",
    "MarksheetSchema",
    "VoterIDSchema"
]
