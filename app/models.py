from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from app.database import Base
from sqlalchemy.dialects.postgresql import ARRAY


Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)

# Связь многие-ко-многим между преподавателями и образовательными программами
teacher_program_association = Table(
    'teacher_programs', Base.metadata,
    Column('teacher_id', Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE")),
    Column('program_id', Integer, ForeignKey('education_programs.program_id', ondelete="CASCADE"))
)

# Таблица преподавателей
class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор преподавателя
    full_name = Column(String(255), unique=True, nullable=False)  # Полное имя преподавателя
    position = Column(String(255), nullable=False)  # Должность преподавателя
    education_level = Column(Text, nullable=False)  # Уровень профессионального образования
    qualification = Column(String(255))  # Квалификация преподавателя
    base_education_specialty = Column(String(255))  # Специальность базового образования
    scientific_education_specialty = Column(String(255))  # Специальность научного образования
    academic_degree = Column(String(255))  # Учёная степень
    academic_title = Column(String(255))  # Учёное звание
    total_experience = Column(Integer)  # Общий стаж работы (в годах)
    teaching_experience = Column(Integer)  # Педагогический стаж (в годах)
    professional_experience = Column(Integer)  # Профессиональный стаж (в годах)
    disciplines_raw = Column(Text)  # Дисциплины, которые ведет преподаватель (в формате JSON)

    # Связи
    qualifications = relationship("Qualification", back_populates="teacher", cascade="all, delete", lazy="selectin")
    retrainings = relationship("Retraining", back_populates="teacher", cascade="all, delete", lazy="selectin")
    # disciplines = relationship("TaughtDiscipline", back_populates="teacher", cascade="all, delete", lazy="selectin")
    # Связь с дисциплинами через таблицу TaughtDiscipline
    taught_disciplines = relationship("TaughtDiscipline", back_populates="teacher", overlaps="disciplines,curriculum")
    disciplines = relationship("Curriculum", secondary="taught_disciplines", back_populates="teachers", lazy="joined", overlaps="taught_disciplines,curriculum")
    programs = relationship("EducationProgram", secondary=teacher_program_association, back_populates="teachers")
    curriculum = relationship("Curriculum", secondary="taught_disciplines", overlaps="teachers", back_populates="teachers")

# Таблица квалификаций преподавателей
class Qualification(Base):
    __tablename__ = "qualifications"

    qualification_id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор квалификации
    program_name = Column(Text, nullable=False)  # Название программы повышения квалификации
    year = Column(Integer, nullable=False)  # Год прохождения программы

    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id", ondelete="CASCADE"), nullable=False)  # Связь с преподавателем
    teacher = relationship("Teacher", back_populates="qualifications", lazy="selectin")

# Таблица переподготовок преподавателей
class Retraining(Base):
    __tablename__ = "retrainings"

    retraining_id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор переподготовки
    teacher_id = Column(Integer, ForeignKey('teachers.teacher_id', ondelete="CASCADE"), nullable=False)  # Связь с преподавателем
    program_name = Column(Text, nullable=False)  # Название программы переподготовки
    year = Column(Integer, nullable=False)  # Год прохождения программы

    teacher = relationship("Teacher", back_populates="retrainings", lazy="selectin")

# Таблица образовательных программ
class EducationProgram(Base):
    __tablename__ = "education_programs"

    program_id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор программы
    program_name = Column(String(255), unique=True, nullable=False)  # Полное название программы
    short_name = Column(String(255), unique=True, nullable=True, index=True)  # Сокращенное название программы (может быть NULL)
    year = Column(Integer, nullable=False)  # Год прохождения программы

    # Связи
    teachers = relationship("Teacher", secondary=teacher_program_association, back_populates="programs", lazy="selectin")
    curriculum = relationship("Curriculum", back_populates="program")  # Связь с учебными планами


class TaughtDiscipline(Base):
    __tablename__ = "taught_disciplines"

    discipline_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id", ondelete="CASCADE"), nullable=False)
    curriculum_id = Column(Integer, ForeignKey("curriculum.curriculum_id", ondelete="CASCADE"), nullable=False)

    teacher = relationship("Teacher", back_populates="taught_disciplines", overlaps="disciplines,curriculum")
    curriculum = relationship("Curriculum", back_populates="taught_disciplines", overlaps="teachers,disciplines")

# Таблица учебных планов
class Curriculum(Base):
    __tablename__ = "curriculum"
    
    curriculum_id = Column(Integer, primary_key=True)  # Уникальный идентификатор учебного плана
    discipline = Column(String(255), nullable=False)  # Название дисциплины
    department = Column(String(255), nullable=False)  # Название кафедры
    semester = Column(ARRAY(Integer), nullable=True)  # Семестр, в котором преподается дисциплина
    lecture_hours = Column(Float, default=0.0)  # Количество часов лекций
    practice_hours = Column(Float, default=0.0)  # Количество часов практических занятий
    lab_hours = Column(Float, default=0.0)
    exam_hours = Column(Float, default=0.0)  # Количество часов экзамена
    test_hours = Column(Float, default=0.0)  # Количество часов зачета
    course_project_hours = Column(Float, default=0.0)  # Количество часов на курсовой проект
    total_practice_hours = Column(Float, default=0.0)  # Общее количество часов практики
    final_work_hours = Column(Integer, default=0)  # Количество часов на выполнение выпускной квалификационной работы
    program_id = Column(Integer, ForeignKey('education_programs.program_id'))  # Связь с образовательной программой
    
    program = relationship("EducationProgram", back_populates="curriculum")  # Связь с образовательной программой
    
    # Добавляем связь с преподавателями через таблицу TaughtDiscipline
    teachers = relationship("Teacher", secondary="taught_disciplines", back_populates="curriculum", lazy="joined", overlaps="taught_disciplines,curriculum")
    taught_disciplines = relationship("TaughtDiscipline", back_populates="curriculum", overlaps="teachers,disciplines")
    
    @property
    def program_short_name(self):
        return self.program.short_name if self.program else None

