from docx import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
from app.models import Teacher, Qualification, EducationProgram, TaughtDiscipline, Base
from database import SQLALCHEMY_DATABASE_URL

# Настройки БД
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Создание таблиц (если их нет)
Base.metadata.create_all(bind=engine)

def parse_docx(file_path):
    doc = Document(file_path)
    table = doc.tables[0]  # Берём первую таблицу в документе

    # Парсим заголовки для сопоставления колонок
    headers = [cell.text.strip() for cell in table.rows[0].cells]

    teachers = []
    for row in table.rows[1:]:  # Пропускаем заголовок
        cells = [cell.text.strip() for cell in row.cells]
        if not any(cells):  # Пропускаем пустые строки
            continue

        # Маппинг данных по заголовкам
        data = {}
        for idx, header in enumerate(headers):
            data[header] = cells[idx]

        # Обработка данных
        teacher = {
            "full_name": data.get("Ф.И.О.", ""),
            "position": data.get("Должность преподавателя", ""),
            "education_level": data.get("Уровень (уровни) профессионального образования, квалификация", ""),
            "academic_degree": data.get("Учёная степень (при наличии)", ""),
            "academic_title": data.get("Учёное звание (при наличии)", ""),
            "total_experience": int(data.get("Общий стаж работы**", 0)),
            "teaching_experience": int(data.get("Стаж работы по специальности", 0)),
            "disciplines_raw": data.get("Перечень преподаваемых дисциплин", ""),
            "qualifications_raw": data.get("Сведения о повышении квалификации (за последние 3 года) и сведения о профессиональной переподготовке (при наличии)", ""),
            "programs_raw": data.get("Наименование образовательных программ, в реализации которых участвует педагогический работник", "")
        }
        teachers.append(teacher)

    return teachers

def import_to_db(teachers_data):
    for entry in teachers_data:
        # Создание преподавателя
        teacher = Teacher(
            full_name=entry["full_name"],
            position=entry["position"],
            education_level=entry["education_level"],
            academic_degree=entry["academic_degree"] if entry["academic_degree"] != "отсутствует" else None,
            academic_title=entry["academic_title"] if entry["academic_title"] != "отсутствует" else None,
            total_experience=entry["total_experience"],
            teaching_experience=entry["teaching_experience"],
            professional_experience=entry["teaching_experience"]  # Из ваших данных
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

        # Добавление дисциплин
        disciplines = [d.strip() for d in entry["disciplines_raw"].split(";") if d.strip()]
        for disc in disciplines:
            discipline = TaughtDiscipline(discipline_name=disc, teacher_id=teacher.teacher_id)
            db.add(discipline)

        # Обработка квалификаций
        quals = re.split(r'(?<=\d{4}\.)\s*', entry["qualifications_raw"])
        for qual in quals:
            if not qual.strip():
                continue
            year_match = re.search(r'\b(\d{4})\.?$', qual)
            year = int(year_match.group(1)) if year_match else None
            course_name = re.sub(r'\s*\d{2}\.\d{2}\.\d{4}\.*\s*$', '', qual).strip()
            if course_name and year:
                qual_entry = Qualification(course_name=course_name, year=year, teacher_id=teacher.teacher_id)
                db.add(qual_entry)

        # Обработка образовательных программ
        programs = [p.strip() for p in entry["programs_raw"].split(";") if p.strip()]
        for prog in programs:
            program = db.query(EducationProgram).filter_by(program_name=prog).first()
            if not program:
                program = EducationProgram(program_name=prog)
                db.add(program)
                db.commit()
                db.refresh(program)
            teacher.programs.append(program)

        db.commit()

if __name__ == "__main__":
    file_path = "АИС МАГИ (1).docx"  # Укажите путь к вашему файлу
    teachers_data = parse_docx(file_path)
    import_to_db(teachers_data)
    print("Данные успешно импортированы!")