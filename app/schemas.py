from pydantic import BaseModel
from typing import List, Optional

class QualificationBase(BaseModel):
    program_name: str
    year: int

    class Config:
        from_attributes = True

class TeacherCreate(BaseModel):
    full_name: str
    position: str
    education_level: str
    qualifications: List[QualificationBase] = []

class TeacherResponse(BaseModel):
    teacher_id: int
    full_name: str
    qualifications: List[QualificationBase]  # Убедитесь, что используется правильная схема
    class Config:
        from_attributes = True  # Для работы с ORM объектами