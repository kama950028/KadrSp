from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Связь многие-ко-многим между преподавателями и программами
teacher_program_association = Table(
    'teacher_programs', Base.metadata,
    Column('teacher_id', Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE")),
    Column('program_id', Integer, ForeignKey('education_programs.program_id', ondelete="CASCADE"))
)

class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), unique=True, nullable=False)
    position = Column(String(100), nullable=False)
    education_level = Column(String(100), nullable=False)
    qualification = Column(String(100))
    base_education_specialty = Column(String(255))
    scientific_education_specialty = Column(String(255))
    academic_degree = Column(String(100))
    academic_title = Column(String(100))
    total_experience = Column(Integer)  # в годах
    teaching_experience = Column(Integer)
    professional_experience = Column(Integer)

    # Связи
    qualifications = relationship("Qualification", back_populates="teacher", cascade="all, delete", lazy="selectin")
    retrainings = relationship("Retraining", back_populates="teacher", cascade="all, delete", lazy="selectin")
    disciplines = relationship("TaughtDiscipline", back_populates="teacher", cascade="all, delete", lazy="selectin")
    programs = relationship(
        "EducationProgram", 
        secondary=teacher_program_association,
        back_populates="teachers"
    )

class Qualification(Base):
    __tablename__ = "qualifications"

    qualification_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE"), nullable=False)
    course_name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)

    teacher = relationship("Teacher", back_populates="qualifications", lazy="selectin")

class Retraining(Base):
    __tablename__ = "retrainings"

    retraining_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE"), nullable=False)
    program_name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)

    teacher = relationship("Teacher", back_populates="retrainings", lazy="selectin")

class EducationProgram(Base):
    __tablename__ = "education_programs"

    program_id = Column(Integer, primary_key=True, index=True)
    program_name = Column(String(255), unique=True, nullable=False)

    teachers = relationship(
        "Teacher", 
        secondary=teacher_program_association,
        back_populates="programs", lazy="selectin"
    )

class TaughtDiscipline(Base):
    __tablename__ = "taught_disciplines"

    discipline_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE"), nullable=False)
    discipline_name = Column(String(255), nullable=False)

    teacher = relationship("Teacher", back_populates="disciplines", lazy="selectin")