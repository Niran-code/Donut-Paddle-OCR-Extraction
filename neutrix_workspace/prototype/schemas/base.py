from pydantic import BaseModel, ConfigDict
from typing import Optional

class BaseDocumentSchema(BaseModel):
    model_config = ConfigDict(extra='allow')
    document_type: str
    ocr_accuracy_score: Optional[float] = None
    face_image: Optional[str] = None
