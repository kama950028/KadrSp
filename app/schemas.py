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


# class CurriculumBase(BaseModel):
    # discipline: str
    # department: str
    # lecture_hours: float
    # exam_hours: float
    # course_project_hours: float
    # final_work_hours: int
    # semester: Optional[int]
    # practice_hours: float
    # test_hours: float
    # total_practice_hours: float
    # program_id: Optional[int]
    # program_short_name: Optional[str]  # Добавлено поле для short_name

    # class Config:
    #     orm_mode = True  # Позволяет работать с объектами SQLAlchemy


from pydantic import BaseModel
from typing import List, Optional

class TeacherBase(BaseModel):
    teacher_id: int
    full_name: str
    position: str

    class Config:
        from_attributes = True  # Для работы с SQLAlchemy-моделями


class CurriculumBase(BaseModel):
    curriculum_id: int
    discipline: str
    department: str
    teachers: List[TeacherBase] = []  # Добавлено поле с преподавателями

    class Config:
        from_attributes = True

class EducationProgramBase(BaseModel):
    program_id: int
    program_name: str
    short_name: Optional[str]
    year: int
    curriculum: List[CurriculumBase] = []  # Теперь curriculum включает teachers

    class Config:
        from_attributes = True
