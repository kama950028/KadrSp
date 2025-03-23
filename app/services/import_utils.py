from docx import Document
import re
from sqlalchemy import delete
from sqlalchemy.orm import Session, exc
from app.models import Teacher, Qualification, EducationProgram, TaughtDiscipline, Curriculum
import pandas as pd
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



# def parse_excel(file_path: str):
#     # Чтение данных из листов
#     df_svod = pd.read_excel(file_path, sheet_name='ПланСвод', header=2)
#     df_plan = pd.read_excel(file_path, sheet_name='План', header=2)

#     # Отладочный вывод заголовков
#     print("Заголовки столбцов в df_svod:", df_svod.columns.tolist())
#     print("Заголовки столбцов в df_plan:", df_plan.columns.tolist())

#     # Приведение заголовков к стандартному виду
#     df_svod.columns = df_svod.columns.str.strip().str.lower()
#     df_plan.columns = df_plan.columns.str.strip().str.lower()

#     # Исключаем строки с "считать в плане = '-'"
#     df_plan = df_plan[df_plan['считать в плане'] != '-']
#     print("Количество строк в df_plan после фильтрации:", len(df_plan))

#     # Обработка листа "ПланСвод" — берем название дисциплины и кафедру
#     if 'наименование' not in df_svod.columns or 'наименование.1' not in df_svod.columns:
#         raise ValueError("Ожидаемые столбцы 'Наименование' или 'Наименование.1' отсутствуют в листе 'ПланСвод'.")

#     df_svod_clean = df_svod[['наименование', 'наименование.1']].copy()
#     df_svod_clean.columns = ['дисциплина', 'кафедра']

#     # Исключаем строки с текстом "Дисциплины по выбору"
#     df_svod_clean = df_svod_clean[~df_svod_clean['дисциплина'].str.contains("дисциплины по выбору", case=False, na=False)]

#     # Обработка листа "План" — берем часы занятий
#     hours_columns = [
#         col for col in df_plan.columns 
#         if any(keyword in col.lower() for keyword in ['лек', 'пр', 'лаб', 'ср', 'кр'])
#     ]
#     print("Столбцы с часами:", hours_columns)

#     if 'наименование' not in df_plan.columns:
#         raise ValueError("Ожидаемый столбец 'Наименование' отсутствует в листе 'План'.")

#     # Заменяем NaN в столбцах с часами на 0
#     df_plan[hours_columns] = df_plan[hours_columns].fillna(0)

#     df_plan_clean = df_plan[['наименование'] + hours_columns].copy()
#     df_plan_clean.columns = ['дисциплина'] + hours_columns
#     print("df_plan_clean columns:", df_plan_clean.columns.tolist())

#     # Объединяем данные по названию дисциплины
#     df_combined = pd.merge(
#         df_svod_clean,
#         df_plan_clean,
#         on='дисциплина',
#         how='inner'
#     )
#     print("df_combined columns:", df_combined.columns.tolist())

#     # Проверка на пустоту объединенного DataFrame
#     if df_combined.empty:
#         raise ValueError("Объединенный DataFrame df_combined пуст. Проверьте данные в df_svod_clean и df_plan_clean.")

#     # Проверка дисциплин, которые не нашли соответствия
#     unmatched_disciplines = df_svod_clean[~df_svod_clean['дисциплина'].isin(df_combined['дисциплина'])]
#     print("Дисциплины из 'ПланСвод', которые не нашли соответствия в 'План':")
#     print(unmatched_disciplines)

#     # Удаление дубликатов и строк с пустыми названиями
#     df_combined = df_combined.drop_duplicates(subset='дисциплина')
#     df_combined = df_combined[df_combined['дисциплина'].notna()]

#     # Преобразование числовых колонок (замена текста на 0)
#     for col in hours_columns:
#         df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)

#     # Преобразование в список словарей для дальнейшей обработки
#     curriculum_data = []
#     for _, row in df_combined.iterrows():
#         entry = {
#             'discipline': row['дисциплина'],
#             'department': row['кафедра'] if pd.notna(row['кафедра']) else 'Кафедра не указана',
#             'lecture_hours': row.get('лек', 0),
#             'practice_hours': row.get('пр', 0),
#             'test_hours': row.get('зачет', 0),
#             'exam_hours': row.get('экзамен', 0),
#             'course_project_hours': row.get('кр', 0),
#             'total_practice_hours': row.get('пр. подгот', 0)
#         }
#         curriculum_data.append(entry)

#         # Отладочный вывод для каждой дисциплины
#         print(f"Обрабатываемая дисциплина: {entry['discipline']}")
#         print(f"Часы лекций: {entry['lecture_hours']}, Часы практик: {entry['practice_hours']}")

#     return curriculum_data


# def import_curriculum(db: Session, curriculum_data: list):
    # try:
    #     # Очищаем таблицу перед импортом
    #     db.execute(delete(Curriculum))
        
    #     # Преобразуем данные в стандартные Python-тип int/float
    #     for entry in curriculum_data:
    #         entry['lecture_hours'] = int(entry['lecture_hours']) if not pd.isna(entry['lecture_hours']) else 0
    #         entry['practice_hours'] = int(entry['practice_hours']) if not pd.isna(entry['practice_hours']) else 0
    #         entry['test_hours'] = int(entry['test_hours']) if not pd.isna(entry['test_hours']) else 0
    #         entry['exam_hours'] = int(entry['exam_hours']) if not pd.isna(entry['exam_hours']) else 0
    #         entry['course_project_hours'] = int(entry['course_project_hours']) if not pd.isna(entry['course_project_hours']) else 0
    #         entry['total_practice_hours'] = float(entry['total_practice_hours']) if not pd.isna(entry['total_practice_hours']) else 0.0

    #     # Пакетная вставка
    #     db.bulk_insert_mappings(Curriculum, curriculum_data)
    #     db.commit()
    # # except Exception as e:

        # db.rollback()
        # raise e
    


def parse_excel(file_path: str) -> list:
    # Чтение данных из листов
    df_svod = pd.read_excel(file_path, sheet_name='ПланСвод', header=2)
    df_plan = pd.read_excel(file_path, sheet_name='План', header=2)

    # Приведение заголовков к стандартному виду
    df_svod.columns = df_svod.columns.str.strip().str.lower()
    df_plan.columns = df_plan.columns.str.strip().str.lower()

    # Фильтрация df_plan
    df_plan = df_plan[df_plan['считать в плане'] != '-']

    # Обработка листа "ПланСвод"
    df_svod_clean = df_svod[['наименование', 'наименование.1']].copy()
    df_svod_clean.columns = ['дисциплина', 'кафедра']
    df_svod_clean = df_svod_clean[
        ~df_svod_clean['дисциплина'].str.contains("дисциплины по выбору", case=False, na=False)
    ]
    df_svod_clean = df_svod_clean.fillna({'кафедра': 'Кафедра не указана'})

    # Обработка часов для листа "План"
    hours_mapping = {
        'lecture_hours': ['лек'],
        'practice_hours': ['пр'],
        'test_hours': ['зачет'],
        'exam_hours': ['экзамен'],
        'course_project_hours': ['кр'],
        'total_practice_hours': ['пр. подгот', 'подгот']
    }

    hours_data = []
    for _, row in df_plan.iterrows():
        entry = {'дисциплина': row['наименование']}
        
        for target_col, keywords in hours_mapping.items():
            total = 0
            for col in df_plan.columns:
                if any(kw in col.lower() for kw in keywords):
                    val = pd.to_numeric(row[col], errors='coerce')
                    total += val if not pd.isna(val) else 0
            entry[target_col] = int(total)
        
        hours_data.append(entry)

    df_hours = pd.DataFrame(hours_data).fillna(0)

    # Объединение данных
    df_combined = pd.merge(
        df_svod_clean,
        df_hours,
        on='дисциплина',
        how='inner'
    )

    # Фильтрация и очистка
    df_combined = df_combined[
        (df_combined['дисциплина'].notna()) &
        (df_combined['дисциплина'] != '')
    ]
    df_combined['дисциплина'] = df_combined['дисциплина'].str.strip()

    # Формирование результата
    curriculum_data = []
    for _, row in df_combined.iterrows():
        discipline = str(row['дисциплина']).strip()
        
        if not discipline:
            continue
            
        entry = {
            'discipline': discipline,
            'department': row['кафедра'],
            'lecture_hours': int(row['lecture_hours']),
            'practice_hours': int(row['practice_hours']),
            'test_hours': int(row['test_hours']),
            'exam_hours': int(row['exam_hours']),
            'course_project_hours': int(row['course_project_hours']),
            'total_practice_hours': int(row['total_practice_hours'])
        }
        curriculum_data.append(entry)

    return curriculum_data

def validate_curriculum_data(curriculum_data: list) -> list:
    validated_data = []
    for entry in curriculum_data:
        validated_entry = {}
        for key, value in entry.items():
            if key.endswith('_hours'):
                try:
                    validated_entry[key] = int(float(value)) if not pd.isna(value) else 0
                except (TypeError, ValueError):
                    validated_entry[key] = 0
            else:
                validated_entry[key] = value if not pd.isna(value) else None
        validated_data.append(validated_entry)
    return validated_data

def import_curriculum(db: Session, curriculum_data: list):
    try:
        # Валидация данных
        validated_data = validate_curriculum_data(curriculum_data)
        
        # Проверка на пустые названия дисциплин
        invalid_entries = [d for d in validated_data if not d.get('discipline')]
        if invalid_entries:
            raise ValueError(f"Найдены записи без названия дисциплины: {invalid_entries}")
        
        # Очистка таблицы
        db.execute(delete(Curriculum))
        
        # Пакетная вставка
        db.bulk_insert_mappings(Curriculum, validated_data)
        db.commit()
        
        # Отладочный вывод
        print(f"Успешно импортировано {len(validated_data)} записей")
        print("Пример первой записи:", validated_data[0])
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
