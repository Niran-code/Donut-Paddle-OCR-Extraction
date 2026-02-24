from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from .base import BaseDocumentSchema

class SubjectSchema(BaseModel):
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    internal_marks: Optional[str] = None
    external_marks: Optional[str] = None
    total: Optional[str] = None
    result: Optional[str] = None
    grade: Optional[str] = None
    credits: Optional[str] = None

class MarksheetSchema(BaseDocumentSchema):
    document_type: str = "Marksheet"
    student_name: Optional[str] = Field(None, description="Student Name")
    university_name: Optional[str] = Field("Unknown", description="University Name")
    college_name: Optional[str] = Field("Unknown", description="College Name")
    university_seat_number: Optional[str] = Field("Unknown", description="USN/Roll Number")
    semester: Optional[str] = Field("Unknown", description="Semester Number")
    subjects: List[SubjectSchema] = Field(default_factory=list, description="Subjects in this semester")
    semester_1: List[SubjectSchema] = Field(default_factory=list, description="Backlogs Sem 1")
    semester_2: List[SubjectSchema] = Field(default_factory=list, description="Backlogs Sem 2")
    remarks: Optional[Dict[str, str]] = None
