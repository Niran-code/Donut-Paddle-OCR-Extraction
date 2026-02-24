from typing import Dict, Any, Tuple
import logging
from schemas import (
    AadhaarSchema,
    PANSchema,
    DLSchema,
    DrivingLicenseSchema,
    PassportSchema,
    MarksheetSchema,
    VoterIDSchema,
    BaseDocumentSchema
)

logger = logging.getLogger(__name__)

class Validator:
    @staticmethod
    def validate_document(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """
        Validates extracted dict against Pydantic schemas.
        Returns: (is_valid, validated_data_dict, error_msg_if_any)
        """
        doc_type = data.get("document_type", "Unknown")
        
        try:
            if doc_type == "Aadhaar Card":
                validated = AadhaarSchema(**data)
            elif doc_type == "PAN Card":
                validated = PANSchema(**data)
            elif doc_type == "Driving License":
                validated = DLSchema(**data)
            elif doc_type == "driving_license":
                validated = DrivingLicenseSchema(**data)
            elif doc_type == "Passport" or doc_type == "passport":
                validated = PassportSchema(**data)
            elif doc_type == "Marksheet":
                validated = MarksheetSchema(**data)
            elif doc_type == "Voter ID":
                validated = VoterIDSchema(**data)
            else:
                validated = BaseDocumentSchema(**data)
                
            return True, validated.model_dump(), ""
            
        except ValueError as ve:
             error_msg = str(ve)
             logger.warning(f"Validation failed for {doc_type}: {error_msg}")
             return False, data, error_msg
        except Exception as e:
             error_msg = f"Unexpected validation error: {str(e)}"
             logger.error(error_msg)
             return False, data, error_msg
