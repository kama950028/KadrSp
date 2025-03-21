from pydantic import BaseModel
from typing import List, Optional

class QualificationBase(BaseModel):
    course_name: str
    year: int

class TeacherCreate(BaseModel):
    full_name: str
    position: str
    education_level: str
    qualifications: List[QualificationBase] = []

class TeacherResponse(TeacherCreate):
    teacher_id: int

    class Config:
        orm_mode = True  # Для работы с ORM объектами