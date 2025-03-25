from docx import Document
import re, math
from sqlalchemy import delete
from sqlalchemy.orm import Session, exc
from app.models import Teacher, Qualification, EducationProgram, TaughtDiscipline, Curriculum
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

def parse_docx(file_path: str):
    doc = Document(file_path)
    table = doc.tables[0]
    headers = [cell.text.strip().replace("\n", " ").replace("\t", " ") for cell in table.rows[0].cells]
    # print(f"Headers: {headers}")  # Отладочный вывод заголовков
    teachers = []

    for row in table.rows[1:]:
        cells = [cell.text.strip().replace("\n", " ").replace("\t", " ") for cell in row.cells]
        if not any(cells):
            continue

        data = {headers[i]: cells[i] for i in range(len(headers))}
        # print(f"Row data: {data}")  # Отладочный вывод данных строки
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
        # print(f"Parsed teacher: {teacher}")  # Отладочный вывод
        teachers.append(teacher)
    return teachers




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

# def determine_program_type(file_name: str) -> str:
#     """
#     Определяет тип программы (бакалавриат или магистратура) на основе названия файла.
#     Формат названия файла: КодНаправленияПодготовки_АббревиатураПрофиля_Институт_ГодПоступления
#     Пример: 09.04.04_АИС_ИИТ_2024
#     """
#     try:
#         # Извлекаем код направления подготовки из названия файла
#         code = file_name.split("_")[0]
#         if code.startswith("09.03"):
#             return "Бакалавриат"
#         elif code.startswith("09.04"):
#             return "Магистратура"
#         else:
#             return "Неизвестный тип программы"
#     except IndexError:
#         return "Ошибка в формате названия файла"
    
def parse_semester(semester_str):
    """Извлекает номера семестров из строки."""
    if pd.isna(semester_str) or not semester_str:
        return []
    semesters = []
    for part in str(semester_str).split(';'):
        try:
            semesters.append(int(float(part.strip())))
        except ValueError:
            continue
    return semesters


def parse_excel(file_path: str) -> list:
    # Чтение данных из листов
    df_svod = pd.read_excel(file_path, sheet_name='ПланСвод', header=2)
    df_plan = pd.read_excel(file_path, sheet_name='План', header=2)

    # Вывод названий столбцов для отладки
    print("Заголовки столбцов в листе 'ПланСвод':", df_svod.columns.tolist())
    print("Заголовки столбцов в листе 'План':", df_plan.columns.tolist())

    # Приведение заголовков к стандартному виду
    df_svod.columns = df_svod.columns.str.strip().str.lower()
    df_plan.columns = df_plan.columns.str.strip().str.lower()

    # Обработка листа "ПланСвод"
    df_svod_clean = df_svod[['наименование', 'наименование.1']].copy()
    df_svod_clean.columns = ['дисциплина', 'кафедра']
    df_svod_clean = df_svod_clean[
        ~df_svod_clean['дисциплина'].str.contains("дисциплины по выбору", case=False, na=False)
    ]
    df_svod_clean = df_svod_clean.fillna({'кафедра': 'Кафедра не указана'})

    # Обработка листа "План"
    df_plan = df_plan[df_plan['считать в плане'] != '-']
    df_plan = df_plan.rename(columns={'наименование': 'дисциплина'})

    # Объединение данных
    df_combined = pd.merge(
        df_svod_clean,
        df_plan,
        on='дисциплина',
        how='inner'
    ).fillna(0)

    # Вспомогательные функции
    def safe_float(value, default=0.0):
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return default

    def sum_columns(df, base_name):
        """Суммирует значения всех столбцов, начинающихся с base_name"""
        matching_columns = [col for col in df.columns if col.startswith(base_name)]
        return df[matching_columns].sum(axis=1)

    # Суммируем значения для лекций, практик и других столбцов
    df_combined['лекции'] = sum_columns(df_combined, 'лек')
    df_combined['практики'] = sum_columns(df_combined, 'пр')
    df_combined['лабораторные'] = sum_columns(df_combined, 'лаб')
    df_combined['курсовые'] = sum_columns(df_combined, 'кп') + sum_columns(df_combined, 'кр')

    # Обработка данных
    curriculum_data = []
    for _, row in df_combined.iterrows():
        discipline = str(row.get('дисциплина', '')).strip()

        # Пропускаем строки с некорректным названием дисциплины
        if not discipline or discipline == "0":
            print(f"Пропущена дисциплина с некорректным названием: {discipline}")
            continue
        
        # Извлечение семестров из столбцов
        semesters = set()
        for col in ['экза мен', 'зачет', 'зачет с оц.']:
            semesters.update(parse_semester(row.get(col, None)))

        # Если семестры не указаны, добавляем запись без семестра
        if not semesters:
            semesters = [None]

        # Создаем запись для каждого семестра
        for semester in semesters:
            # Расчет часов для зачета и экзамена
            test_hours = 0.25 if row.get('зачет', 0) > 0 else 0
            exam_hours = 2.35 if row.get('экза мен', 0) > 0 else 0

            entry = {
                'discipline': discipline,
                'department': str(row.get('кафедра', 'Кафедра не указана')),
                'lecture_hours': safe_float(row.get('лекции', 0)),
                'practice_hours': safe_float(row.get('практики', 0)),
                'test_hours': test_hours,
                'exam_hours': exam_hours,
                'course_project_hours': safe_float(row.get('курсовые', 0)),
                'total_practice_hours': 0.0,
                'final_work_hours': 0,
                'semester': semester  # Добавляем семестр
            }

            # Расчет общего времени практики
            entry['total_practice_hours'] = round(
                entry['lecture_hours'] +
                entry['practice_hours'] +
                entry['test_hours'] +
                entry['exam_hours'],
                2
            )

            # Обработка выпускной работы
            if "выполнение и защита выпускной квалификационной работы" in entry['discipline'].lower():
                entry['final_work_hours'] = 18  # Пример для бакалавриата

            # Замена NaN/Inf
            for key in entry:
                if isinstance(entry[key], float):
                    if math.isnan(entry[key]) or math.isinf(entry[key]):
                        entry[key] = 0.0

            curriculum_data.append(entry)

    return curriculum_data


def import_curriculum(db: Session, curriculum_data: list):
    try:
        # Проверка данных
        invalid = [d for d in curriculum_data if not isinstance(d.get('discipline'), str)]
        if invalid:
            raise ValueError(f"Найдено {len(invalid)} некорректных записей")

        # Очистка таблицы
        db.execute(delete(Curriculum))
        
        # Пакетная вставка
        db.bulk_insert_mappings(Curriculum, curriculum_data)
        db.commit()
        
        print(f"Импортировано {len(curriculum_data)} записей")
        return True
    
    except Exception as e:
        db.rollback()
        raise e