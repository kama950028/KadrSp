from pydantic import BaseModel, validator
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



class TeacherBase(BaseModel):
    teacher_id: int
    full_name: str
    position: str

    class Config:
        from_attributes = True  # Для работы с SQLAlchemy-моделями


class CurriculumBase(BaseModel):
    discipline: str
    department: Optional[str]
    semester: Optional[List[int]] = None  # Теперь здесь будет int
    lecture_hours: Optional[int]
    practice_hours: Optional[int]
    exam_hours: Optional[float]
    test_hours: Optional[float]
    teachers: List[TeacherBase] = []
    total_practice_hours: Optional[float]

    # # Добавьте кастомный валидатор
    @validator("semester", pre=True)
    def convert_semester(cls, value):
        if isinstance(value, int):
            return [value]  # Преобразует число в список
        return value  # Оставляет список без изменений


    class Config:
        orm_mode = True

class EducationProgramBase(BaseModel):
    program_id: int
    program_name: str
    short_name: Optional[str]
    year: int
    curriculum: List[CurriculumBase] = []  # Теперь curriculum включает teachers

    class Config:
        from_attributes = True
