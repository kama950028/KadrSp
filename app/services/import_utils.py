from docx import Document
import re
from sqlalchemy.orm import Session, exc
from app.models import Teacher, Qualification, EducationProgram, TaughtDiscipline
from sqlalchemy.dialects.postgresql import insert

def parse_docx(file_path: str):
    doc = Document(file_path)
    table = doc.tables[0]
    headers = [cell.text.strip().replace("\n", " ").replace("\t", " ") for cell in table.rows[0].cells]
    print(f"Headers: {headers}")  # Отладочный вывод заголовков
    teachers = []

    for row in table.rows[1:]:
        cells = [cell.text.strip().replace("\n", " ").replace("\t", " ") for cell in row.cells]
        if not any(cells):
            continue

        data = {headers[i]: cells[i] for i in range(len(headers))}
        print(f"Row data: {data}")  # Отладочный вывод данных строки
        teacher = {
            "full_name": data.get("Ф.И.О.", ""),
            "position": data.get("Должность преподавателя", ""),
            "education_level": data.get("Уровень (уровни) профессионального образования, квалификация", ""),
            "academic_degree": data.get("Учёная степень (при наличии)", ""),
            "academic_title": data.get("Учёное звание (при наличии)", ""),
            "total_experience": int(data.get("Общий стаж работы", 0)) if data.get("Общий стаж работы", "").isdigit() else 0,
            "teaching_experience": int(data.get("Стаж работы по специальности (сведения о продолжительности опыта (лет) работы в профессиональной сфере)", 0)) if data.get("Стаж работы по специальности (сведения о продолжительности опыта (лет) работы в профессиональной сфере)", "").isdigit() else 0,
            "professional_experience": int(data.get("Профессиональный стаж", 0)) if data.get("Профессиональный стаж", "").isdigit() else 0,
            "disciplines_raw": data.get("Перечень преподаваемых дисциплин", ""),
            "qualifications_raw": data.get("Сведения о повышении квалификации (за последние 3 года) и сведения о профессиональной переподготовке (при наличии)", ""),
            "programs_raw": data.get("Наименование образовательных программ, в реализации которых участвует педагогический работник", "")
        }
        print(f"Parsed teacher: {teacher}")  # Отладочный вывод
        teachers.append(teacher)
    return teachers

# def import_teachers(db: Session, teachers_data: list):
#     for entry in teachers_data:
#         # Проверка на существование
#         existing = db.query(Teacher).filter_by(full_name=entry["full_name"]).first()
#         if existing:
#             continue

#         teacher = Teacher(
#             full_name=entry["full_name"],
#             position=entry["position"],
#             education_level=entry["education_level"],
#             academic_degree=entry["academic_degree"] if entry["academic_degree"] != "отсутствует" else None,
#             academic_title=entry["academic_title"] if entry["academic_title"] != "отсутствует" else None,
#             total_experience=entry["total_experience"],
#             teaching_experience=entry["teaching_experience"],
#             professional_experience=entry["teaching_experience"]
#         )
#         db.add(teacher)
#         db.commit()
#         db.refresh(teacher)

#     try:
#         db.commit()
#     except IntegrityError:
#         db.rollback()
#         raise    


def import_teachers(db: Session, teachers_data: list):
    for entry in teachers_data:
        # Вставка преподавателя с обработкой конфликтов
        stmt = (
            insert(Teacher)
            .values(
                full_name=entry["full_name"],
                position=entry["position"],
                education_level=entry["education_level"],
                academic_degree=entry["academic_degree"],
                academic_title=entry["academic_title"],
                total_experience=entry["total_experience"],
                teaching_experience=entry["teaching_experience"],
                professional_experience=entry["professional_experience"]
            )
            .on_conflict_do_nothing(index_elements=["full_name"])
            .returning(Teacher.teacher_id)  # Получаем ID вставленной записи
        )

        result = db.execute(stmt).fetchone()
        if not result:  # Если запись уже существует
            teacher_id = db.query(Teacher).filter_by(full_name=entry["full_name"]).first().teacher_id
        else:
            teacher_id = result[0]

        # Добавление дисциплин
        disciplines = [d.strip() for d in entry["disciplines_raw"].split(";") if d.strip()]
        for disc in disciplines:
            db.add(TaughtDiscipline(discipline_name=disc, teacher_id=teacher_id))

        # Обработка квалификаций
        quals = re.split(r'(?<=\d{4}\.)\s*', entry["qualifications_raw"])
        for qual in quals:
            if not qual.strip():
                continue
            year_match = re.search(r'\b(\d{4})\.?$', qual)
            year = int(year_match.group(1)) if year_match else None
            course_name = re.sub(r'\s*\d{2}\.\d{2}\.\d{4}\.*\s*$', '', qual).strip()
            if course_name and year:
                db.add(Qualification(program_name=course_name, year=year, teacher_id=teacher_id))

        # Обработка программ
        programs = [p.strip() for p in entry["programs_raw"].split(";") if p.strip()]
        for prog in programs:
            program = db.query(EducationProgram).filter(EducationProgram.program_name == prog).first()
            if not program:
                program = EducationProgram(program_name=prog)
                db.add(program)
                db.commit()
                db.refresh(program)
            teacher = db.query(Teacher).filter_by(teacher_id=teacher_id).first()
            teacher.programs.append(program)
        
        db.commit()