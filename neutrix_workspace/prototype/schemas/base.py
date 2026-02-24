from pydantic import BaseModel
from typing import Optional

class BaseDocumentSchema(BaseModel):
    document_type: str
    ocr_accuracy_score: Optional[float] = None
    face_image: Optional[str] = None
