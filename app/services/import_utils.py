from docx import Document
import re, math, csv
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



def import_teachers_with_programs(db: Session, teachers_data: list):
    """
    Импортирует преподавателей и привязывает их к образовательным программам.
    """
    for entry in teachers_data:
        # Проверяем, существует ли преподаватель
        teacher = db.query(Teacher).filter_by(full_name=entry["full_name"]).first()
        if not teacher:
            # Создаем нового преподавателя
            teacher = Teacher(
                full_name=entry["full_name"],
                position=entry["position"],
                education_level=entry["education_level"],
                total_experience=entry.get("total_experience", 0),
                teaching_experience=entry.get("teaching_experience", 0),
                professional_experience=entry.get("professional_experience", 0),
                academic_degree=entry.get("academic_degree"),
                academic_title=entry.get("academic_title")
            )
            db.add(teacher)
            db.commit()
            db.refresh(teacher)

        # Обработка образовательных программ
        programs_raw = entry.get("programs_raw", "")
        programs = [p.strip() for p in programs_raw.split(";") if p.strip()]  # Разделяем и очищаем программы

        for program_name in programs:
            # Проверяем, существует ли программа
            program = db.query(EducationProgram).filter_by(program_name=program_name).first()
            if not program:
                # Генерация уникального short_name
                base_short_name = program_name[:10].strip()  # Берем первые 10 символов
                short_name = base_short_name
                counter = 1

                # Проверяем уникальность short_name
                while db.query(EducationProgram).filter_by(short_name=short_name).first():
                    short_name = f"{base_short_name}_{counter}"
                    counter += 1

                # Создаем новую программу
                program = EducationProgram(program_name=program_name, short_name=short_name, year=2023)
                db.add(program)
                db.commit()
                db.refresh(program)

            # Привязываем преподавателя к программе
            if program not in teacher.programs:
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
            
        # Проверяем, содержит ли дисциплина слово "практика"
        if "практика" in discipline.lower():
            for semester in semesters:
                exam_hours = safe_float(row.get('конт. раб.', 0))  # Берем часы из столбца "Конт. раб."
                entry = {
                    'discipline': discipline,
                    'department': str(row.get('кафедра', 'Кафедра не указана')),
                    'semester': semester,
                    'final_work_hours': 0,
                    'lecture_hours': 0.0,
                    'practice_hours': 0.0,
                    'test_hours': 0.0,
                    'exam_hours': exam_hours,  # Часы из "Конт. раб."
                    'course_project_hours': 0.0,
                    'total_practice_hours': exam_hours  # Общее время практики равно exam_hours
                }
                curriculum_data.append(entry)
            continue  # Пропускаем стандартную обработку

        # Проверяем, содержит ли дисциплина слова "Выполнение и защита выпускной"
        if "выполнение и защита выпускной" in discipline.lower():
            for semester in semesters:
                final_work_hours = 18  # Пример значения для выпускной работы
                entry = {
                    'discipline': discipline,
                    'department': str(row.get('кафедра', 'Кафедра не указана')),
                    'semester': semester,
                    'final_work_hours': final_work_hours,
                    'lecture_hours': 0.0,
                    'practice_hours': 0.0,
                    'test_hours': 0.0,
                    'exam_hours': 0.0,
                    'course_project_hours': 0.0,
                    'total_practice_hours': final_work_hours  # Суммируем данные (равно final_work_hours)
                }
                curriculum_data.append(entry)
            continue  # Пропускаем стандартную обработку

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

def assign_teacher_to_program(db: Session, teacher_id: int, program_id: int):
    """
    Привязывает преподавателя к образовательной программе.
    """
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    program = db.query(EducationProgram).filter(EducationProgram.program_id == program_id).first()

    if not teacher:
        raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
    if not program:
        raise ValueError(f"Образовательная программа с ID {program_id} не найдена")

    # Добавляем программу в список программ преподавателя
    if program not in teacher.programs:
        teacher.programs.append(program)
        db.commit()
        print(f"Преподаватель {teacher.full_name} привязан к программе {program.program_name}")
    else:
        print(f"Преподаватель {teacher.full_name} уже привязан к программе {program.program_name}")


# def import_curriculum(db: Session, curriculum_data: list):
#     try:
#         # Проверка данных
#         invalid = [d for d in curriculum_data if not isinstance(d.get('discipline'), str)]
#         if invalid:
#             raise ValueError(f"Найдено {len(invalid)} некорректных записей")

#         # Очистка таблицы
#         db.execute(delete(Curriculum))
        
#         # Связывание дисциплин с образовательными программами
#         for entry in curriculum_data:
#             program_short_name = entry.get('program_short_name')
#             if program_short_name:
#                 program = db.query(EducationProgram).filter_by(short_name=program_short_name).first()
#                 if program:
#                     entry['program_id'] = program.program_id
#                 else:
#                     print(f"Программа с short_name '{program_short_name}' не найдена")

#         # Пакетная вставка
#         db.bulk_insert_mappings(Curriculum, curriculum_data)
#         db.commit()
        
#         print(f"Импортировано {len(curriculum_data)} записей")
#         return True
    
#     except Exception as e:
#         db.rollback()
#         raise e
    
def import_curriculum(db: Session, curriculum_data: list):
    """
    Импортирует учебные планы и связывает их с выбранной образовательной программой.
    """
    try:
        # Получаем список доступных образовательных программ
        programs = db.query(EducationProgram).all()
        if not programs:
            raise ValueError("Нет доступных образовательных программ. Сначала создайте их.")

        # Выводим список программ для выбора
        print("Доступные образовательные программы:")
        for i, program in enumerate(programs, start=1):
            print(f"{i}. {program.program_name} (short_name: {program.short_name}, year: {program.year})")

        # Запрашиваем выбор пользователя
        selected_index = int(input("Введите номер образовательной программы: ")) - 1
        if selected_index < 0 or selected_index >= len(programs):
            raise ValueError("Неверный выбор программы.")

        selected_program = programs[selected_index]
        print(f"Вы выбрали программу: {selected_program.program_name} (ID: {selected_program.program_id})")

        # Добавляем program_id ко всем записям учебного плана
        for entry in curriculum_data:
            entry['program_id'] = selected_program.program_id

        # Проверка данных
        invalid = [d for d in curriculum_data if not isinstance(d.get('discipline'), str)]
        if invalid:
            raise ValueError(f"Найдено {len(invalid)} некорректных записей")

        # Очистка таблицы (если требуется)
        db.execute(delete(Curriculum))

        # Пакетная вставка
        db.bulk_insert_mappings(Curriculum, curriculum_data)
        db.commit()

        print(f"Импортировано {len(curriculum_data)} записей для программы '{selected_program.program_name}'")
        return True

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Ошибка импорта учебных планов: {e}")


def check_duplicates_in_csv(file_path: str):
    """
    Проверяет наличие дубликатов в столбце short_name в CSV-файле.
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        short_names = set()
        duplicates = set()
        
        for row in reader:
            short_name = row['short_name'].strip()
            if short_name in short_names:
                duplicates.add(short_name)
            else:
                short_names.add(short_name)
        
        if duplicates:
            raise ValueError(f"Найдены дубликаты в CSV-файле: {', '.join(duplicates)}")
        
def remove_duplicates_from_csv(file_path: str, output_file_path: str):
    """
    Удаляет дубликаты из CSV-файла на основе поля short_name и сохраняет результат в новый файл.
    """
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            unique_rows = {}
            
            for row in reader:
                short_name = row['short_name'].strip()
                # Если short_name уже есть, пропускаем запись
                if short_name not in unique_rows:
                    unique_rows[short_name] = row
            
        # Сохраняем уникальные записи в новый файл
        with open(output_file_path, mode='w', encoding='utf-8', newline='') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(unique_rows.values())
        
        print(f"Дубликаты удалены. Уникальные записи сохранены в файл: {output_file_path}")
    except Exception as e:
        raise RuntimeError(f"Ошибка при удалении дубликатов: {e}")

def import_education_programs(file_path: str, db: Session):
    """
    Импортирует образовательные программы из CSV-файла в таблицу education_programs.
    Если программа с таким short_name уже существует, она обновляется.
    """
    try:
        # Удаляем дубликаты перед импортом
        cleaned_file_path = "cleaned_" + file_path
        remove_duplicates_from_csv(file_path, cleaned_file_path)
        
        with open(cleaned_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                program_name = row['program_name'].strip()
                short_name = row['short_name'].strip()
                year = int(row['year'])

                # Проверяем, существует ли запись с таким short_name
                existing_program = db.query(EducationProgram).filter_by(short_name=short_name).first()
                if existing_program:
                    # Обновляем существующую запись
                    existing_program.program_name = program_name
                    existing_program.year = year
                else:
                    # Добавляем новую запись
                    new_program = EducationProgram(
                        program_name=program_name,
                        short_name=short_name,
                        year=year
                    )
                    db.add(new_program)
            
            db.commit()
            print("Импорт завершен.")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Ошибка импорта образовательных программ: {e}")