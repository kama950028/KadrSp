from docx import Document
import re, math, csv
from sqlalchemy import delete
from sqlalchemy.orm import Session, exc
from app.models import (
    Teacher,
    Qualification,
    EducationProgram,
    TaughtDiscipline,
    Curriculum,
)
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from io import BytesIO
import traceback
from fastapi import HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import re
import os
from datetime import datetime
from typing import List, Dict
from app.models import Curriculum, EducationProgram
import logging

def parse_docx(file_path: str):
    doc = Document(file_path)
    table = doc.tables[0]
    headers = [
        cell.text.strip().replace("\n", " ").replace("\t", " ")
        for cell in table.rows[0].cells
    ]
    # print(f"Headers: {headers}")  # Отладочный вывод заголовков
    teachers = []

    for row in table.rows[1:]:
        cells = [
            cell.text.strip().replace("\n", " ").replace("\t", " ")
            for cell in row.cells
        ]
        if not any(cells):
            continue

        data = {headers[i]: cells[i] for i in range(len(headers))}
        # print(f"Row data: {data}")  # Отладочный вывод данных строки
        teacher = {
            "full_name": data.get("Ф.И.О.", ""),
            "position": data.get("Должность преподавателя", ""),
            "education_level": data.get(
                "Уровень (уровни) профессионального образования, квалификация", ""
            ),
            "academic_degree": data.get("Учёная степень (при наличии)", ""),
            "academic_title": data.get("Учёное звание (при наличии)", ""),
            "total_experience": (
                int(data.get("Общий стаж работы", 0))
                if data.get("Общий стаж работы", "").isdigit()
                else 0
            ),
            "teaching_experience": (
                int(
                    data.get(
                        "Стаж работы по специальности (сведения о продолжительности опыта (лет) работы в профессиональной сфере)",
                        0,
                    )
                )
                if data.get(
                    "Стаж работы по специальности (сведения о продолжительности опыта (лет) работы в профессиональной сфере)",
                    "",
                ).isdigit()
                else 0
            ),
            "professional_experience": (
                int(data.get("Профессиональный стаж", 0))
                if data.get("Профессиональный стаж", "").isdigit()
                else 0
            ),
            "disciplines_raw": data.get("Перечень преподаваемых дисциплин", ""),
            "qualifications_raw": data.get(
                "Сведения о повышении квалификации (за последние 3 года) и сведения о профессиональной переподготовке (при наличии)",
                "",
            ),
            "programs_raw": data.get(
                "Наименование образовательных программ, в реализации которых участвует педагогический работник",
                "",
            ),
        }
        # print(f"Parsed teacher: {teacher}")  # Отладочный вывод
        teachers.append(teacher)
    return teachers


def import_teachers_with_programs(db: Session, teachers_data: list):
    """
    Импортирует преподавателей, привязывает их к образовательным программам и дисциплинам.
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
                academic_title=entry.get("academic_title"),
            )
            db.add(teacher)
            db.commit()
            db.refresh(teacher)

        # Обработка образовательных программ
        programs_raw = entry.get("programs_raw", "")
        programs = [
            p.strip() for p in programs_raw.split(";") if p.strip()
        ]  # Разделяем строку на отдельные программы

        for program_name in programs:
            # Проверяем, существует ли программа
            program = (
                db.query(EducationProgram).filter_by(program_name=program_name).first()
            )
            if not program:
                # Генерация short_name из профиля в скобках
                profile_match = re.search(r"\((.*?)\)", program_name)
                profile = profile_match.group(1) if profile_match else "UNKNOWN"
                short_name = f"{program_name.split()[0]}_{''.join(word[0] for word in profile.split())}_2023"

                # Проверяем уникальность short_name
                counter = 1
                base_short_name = short_name
                while (
                    db.query(EducationProgram).filter_by(short_name=short_name).first()
                ):
                    short_name = f"{base_short_name}_{counter}"
                    counter += 1

                # Создаем новую программу
                program = EducationProgram(
                    program_name=program_name, short_name=short_name, year=2023
                )
                db.add(program)
                db.commit()
                db.refresh(program)

            # Привязываем преподавателя к программе
            if program not in teacher.programs:
                teacher.programs.append(program)

        # Обработка дисциплин
        disciplines_raw = entry.get("disciplines_raw", "")
        disciplines = [
            d.strip() for d in disciplines_raw.split(";") if d.strip()
        ]  # Разделяем строку на дисциплины

        for discipline_name in disciplines:
            # Приведение названия дисциплины к стандартному виду
            normalized_name = discipline_name.strip().lower()

            # Проверяем, существует ли дисциплина с учётом регистра и лишних пробелов
            discipline = (
                db.query(Curriculum)
                .filter(Curriculum.discipline.ilike(f"%{normalized_name}%"))
                .first()
            )

            if not discipline:
                # Создаем новую дисциплину
                discipline = Curriculum(
                    discipline=discipline_name.strip(), department="Не указано"
                )
                db.add(discipline)
                db.commit()
                db.refresh(discipline)

            # Привязываем преподавателя к дисциплине через TaughtDiscipline
            taught_discipline = (
                db.query(TaughtDiscipline)
                .filter_by(
                    teacher_id=teacher.teacher_id,
                    curriculum_id=discipline.curriculum_id,
                )
                .first()
            )
            if not taught_discipline:
                taught_discipline = TaughtDiscipline(
                    teacher_id=teacher.teacher_id,
                    curriculum_id=discipline.curriculum_id,
                )
                db.add(taught_discipline)

        db.commit()






def assign_teacher_to_program(db: Session, teacher_id: int, program_id: int):
    """
    Привязывает преподавателя к образовательной программе.
    """
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    program = (
        db.query(EducationProgram)
        .filter(EducationProgram.program_id == program_id)
        .first()
    )

    if not teacher:
        raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
    if not program:
        raise ValueError(f"Образовательная программа с ID {program_id} не найдена")

    # Добавляем программу в список программ преподавателя
    if program not in teacher.programs:
        teacher.programs.append(program)
        db.commit()
        print(
            f"Преподаватель {teacher.full_name} привязан к программе {program.program_name}"
        )
    else:
        print(
            f"Преподаватель {teacher.full_name} уже привязан к программе {program.program_name}"
        )






logger = logging.getLogger(__name__)


def safe_convert(value, convert_func, default):
    """Безопасное преобразование значений"""
    try:
        if pd.isna(value) or str(value).strip() in ("", "-", "н/д"):
            return default
        return convert_func(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Ошибка преобразования значения {value}: {e}")
        return default


from collections import defaultdict


def parse_semester(exam_value, test_value):
    """Извлекает номера семестров, объединяя значения через запятую."""
    semesters = []
    
    def parse_value(val):
        try:
            # Извлекаем первое целое число из значения
            numbers = re.findall(r"\d+", str(val))
            if not numbers:
                return None
            num = int(numbers[0])
            return num if num > 0 else None
        except (ValueError, TypeError):
            return None
    
    # Обработка экзамена
    exam_sem = parse_value(exam_value)
    if exam_sem is not None:
        semesters.append(str(exam_sem))
    
    # Обработка зачета
    test_sem = parse_value(test_value)
    if test_sem is not None:
        semesters.append(str(test_sem))
    
    # Возвращаем объединенные значения через запятую или None
    return ", ".join(semesters) if semesters else None

def parse_excel(file_path: str) -> List[Dict]:
    """
    Универсальный парсер учебного плана с поддержкой:
    - переменного количества курсов
    - автоматическим определением структуры файла
    - обработкой различных форматов данных
    """
    try:
        print(f"\n{'='*50}\nНачало обработки файла: {file_path}\n{'='*50}")

        # 1. Чтение и анализ структуры файла
        xls = pd.ExcelFile(file_path)
        print(f"Листы в файле: {xls.sheet_names}")

        # 2. Определение основных колонок в ПланСвод
        df_svod = pd.read_excel(xls, sheet_name="ПланСвод", header=None, nrows=5)
        header_row = None

        # Поиск строки с заголовками
        for i in range(3):  # Проверяем первые 3 строки
            if "Наименование" in df_svod.iloc[i].values:
                header_row = i
                break

        if header_row is None:
            raise ValueError("Не найдена строка с заголовками в листе 'ПланСвод'")

        df_svod = pd.read_excel(xls, sheet_name="ПланСвод", header=header_row)
        print("\nСтруктура листа ПланСвод:")
        print(df_svod.columns.tolist())

        # Автоматическое определение колонок
        disc_col = next(
            (col for col in df_svod.columns if "наименование" in str(col).lower()), None
        )
        dept_col = next(
            (col for col in df_svod.columns if "наименование.1" in str(col).lower()), None
        )

        if not disc_col:
            raise ValueError("Не найдена колонка с названиями дисциплин")

        # 3. Анализ листа План
        df_plan = pd.read_excel(xls, sheet_name="План", header=None, nrows=5)
        plan_header_row = None

        for i in range(3):
            if "Наименование" in df_plan.iloc[i].values:
                plan_header_row = i
                break

        if plan_header_row is None:
            raise ValueError("Не найдена строка с заголовками в листе 'План'")

        df_plan = pd.read_excel(xls, sheet_name="План", header=plan_header_row)
        print("\nСтруктура листа План:")
        print(df_plan.columns.tolist())

        # 4. Определение структуры курсов
        course_blocks = defaultdict(dict)
        current_course = None

        for col in df_plan.columns:
            col_name = str(col)
            current_course = col_name
            print(f"col_name: {col_name} current_course: {current_course}")

            # if "курс" in col_name.lower():
            #     current_course = col_name
            #     course_blocks[current_course] = {"start_col": col}

            # elif current_course:
            if "семестр" in col_name.lower():
                course_blocks[current_course]["semester_col"] = col
            elif "экз" in col_name.lower():
                course_blocks[current_course]["exam_col"] = col
            elif "зачет" in col_name.lower() and not "зачет с оц" in col_name.lower():
                course_blocks[current_course]["test_col"] = col
            elif "лек" in col_name.lower():
                course_blocks[current_course]["lecture_col"] = col
            elif "пр" in col_name.lower() and not "пр пр" in col_name.lower():
                course_blocks[current_course]["practice_col"] = col
            elif "лаб" in col_name.lower():
                course_blocks[current_course]["lab_col"] = col

        print("\nОбнаруженные блоки курсов:")
        for course, blocks in course_blocks.items():
            print(f"{course}: {blocks}")

         # 4. Автопоиск колонок для семестров
        exam_col = next((col for col in df_plan.columns if "экза" in str(col).lower()), None)
        test_col = next((col for col in df_plan.columns if "зачет" in str(col).lower()), None)

        if not exam_col or not test_col:
            available_cols = ", ".join(df_plan.columns)
            raise ValueError(
                f"Не найдены колонки с экзаменами и зачетами. Доступные колонки: {available_cols}"
            )

        print(f"Найдены колонки: Экзамен - '{exam_col}', Зачет - '{test_col}'")

        # 5. Обработка данных
        result = []
        discipline_col_plan = next(
            (col for col in df_plan.columns if "наименование" in str(col).lower()),
            disc_col,
        )

        for idx, row in df_svod.iterrows():
            if pd.isna(row[disc_col]) or str(row[disc_col]).strip() in ["", "nan"]:
                continue

            discipline = str(row[disc_col]).strip()
            if discipline.startswith("Дисциплины по выбору"):
                continue  # Пропустить эту дисциплину

            department = (
                str(row[dept_col]).strip()
                if dept_col and pd.notna(row.get(dept_col))
                else "Не указано"
            )
            
            exam_value = row.get(exam_col, None)
            test_value = row.get(test_col, None)
            semesters = parse_semester(exam_value, test_value)


            # Поиск дисциплины в листе План
            hours_data = None
            if discipline_col_plan in df_plan.columns:
                mask = (
                    df_plan[discipline_col_plan].astype(str).str.strip() == discipline
                )
                if mask.any():
                    hours_data = df_plan[mask].iloc[0]

            # Сбор часов по всем курсам
            lecture_hours = 0.0
            practice_hours = 0.0
            lab_hours = 0.0
            exam_hours = 0.0
            test_hours = 0.0

            for course, blocks in course_blocks.items():
                try:
                    if "lecture_col" in blocks:
                        val = (
                            hours_data[blocks["lecture_col"]]
                            if hours_data is not None
                            else 0
                        )
                        lecture_hours += float(val) if pd.notna(val) else 0

                    if "practice_col" in blocks:
                        val = (
                            hours_data[blocks["practice_col"]]
                            if hours_data is not None
                            else 0
                        )
                        practice_hours += float(val) if pd.notna(val) else 0

                    if "exam_col" in blocks:
                        val = (
                            hours_data[blocks["exam_col"]]
                            if hours_data is not None
                            else 0
                        )
                        exam_hours = int(val) if pd.notna(val) else 0

                    if "test_col" in blocks:
                        val = (
                            hours_data[blocks["test_col"]]
                            if hours_data is not None
                            else 0
                        )
                        test_hours = int(val) if pd.notna(val) else 0

                    if "lab_col" in blocks:
                        val = (
                            hours_data[blocks["lab_col"]]
                            if hours_data is not None
                            else 0
                        )
                        lab_hours += float(val) if pd.notna(val) else 0
                except (ValueError, TypeError):
                    continue

            item = {
                "discipline": discipline,
                "department": department,
                "semester": semesters,
                "lecture_hours": lecture_hours,
                "practice_hours": practice_hours,
                "exam_ours": exam_hours,
                "lab_hours": lab_hours,
                "exam_hours": 0.0,
                "test_hours": test_hours,
                "total_practice_hours": lecture_hours + practice_hours + lab_hours,
            }

            print(f"\nДисциплина: {discipline}")
            print(f"Кафедра: {department}")
            print(f"Часы: лекции={lecture_hours}, практики={practice_hours}, лабы={lab_hours}")
            print(f"Семестр: {semesters if semesters else 'Не указан'}")
            

            result.append(item)

        if not result:
            raise ValueError("Файл не содержит данных для импорта")

        print(f"\n{'='*50}\nУспешно обработано дисциплин: {len(result)}")
        print(f"{'='*50}\n")

        return result

    except Exception as e:
        print(f"\n{'!'*50}\nОшибка при обработке файла: {str(e)}\n{'!'*50}")
        logger.error(f"Ошибка парсинга Excel: {str(e)}", exc_info=True)
        raise ValueError(f"Ошибка чтения файла: {str(e)}")


def import_curriculum(
    file_path: str, filename: str, db: Session, background_tasks: BackgroundTasks
):
    """
    Улучшенная функция импорта учебного плана.
    Включает расширенную диагностику и обработку ошибок.
    """
    try:
        # Проверка файла
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Файл не найден")

        if not filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только файлы Excel (.xlsx, .xls)",
            )

        # Диагностика перед парсингом
        try:
            # Пробуем прочитать файл для диагностики
            diagnostic_df = pd.read_excel(file_path, sheet_name=None, nrows=1)
            print("Диагностика файла:")
            for sheet_name, df in diagnostic_df.items():
                print(f"Лист '{sheet_name}': колонки - {df.columns.tolist()}")
        except Exception as e:
            logger.warning(f"Диагностика файла не удалась: {str(e)}")

        # Парсинг данных
        try:
            curriculum_data = parse_excel(file_path)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": str(e),
                    "advice": "Проверьте, что файл содержит листы 'ПланСвод' и 'План' с корректными колонками",
                },
            )

        if not curriculum_data:
            raise HTTPException(
                status_code=400,
                detail="Файл не содержит данных для импорта. Проверьте формат файла.",
            )

        # Определение программы
        try:
            program_code = filename.split("_")[0]
            program = (
                db.query(EducationProgram)
                .filter(EducationProgram.short_name.ilike(f"{program_code}%"))
                .first()
            )

            if not program:
                available_programs = db.query(EducationProgram.short_name).all()
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": f"Программа с кодом {program_code} не найдена",
                        "available_programs": [
                            p[0] for p in available_programs if p[0]
                        ],
                        "filename_pattern": "Ожидается формат: КОД_ПРОФИЛЬ_ИНСТИТУТ_ГОД.xlsx",
                    },
                )
        except IndexError:
            raise HTTPException(
                status_code=400,
                detail="Некорректное имя файла. Ожидается формат: КОД_ПРОФИЛЬ_ИНСТИТУТ_ГОД.xlsx",
            )

        # Очистка старых данных
        deleted_count = (
            db.query(Curriculum)
            .filter(Curriculum.program_id == program.program_id)
            .delete(synchronize_session=False)
        )
        logger.info(f"Удалено {deleted_count} старых записей учебного плана")

        # Подготовка данных
        for item in curriculum_data:
            item["program_id"] = program.program_id
            item["semester"] = item.get("semester") or None

            # Приведение типов
            for field in [
                "lecture_hours",
                "practice_hours",
                "lab_hours",
                "exam_hours",
                "test_hours",
            ]:
                item[field] = float(item.get(field, 0))

        # Вставка данных
        try:
            db.bulk_insert_mappings(Curriculum, curriculum_data)
            db.commit()
            logger.info(f"Успешно импортировано {len(curriculum_data)} дисциплин")
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при вставке данных: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Ошибка базы данных при импорте: {str(e)}"
            )

        # Очистка
        background_tasks.add_task(
            lambda: os.remove(file_path) if os.path.exists(file_path) else None
        )

        return {
            "status": "success",
            "imported_count": len(curriculum_data),
            "program_id": program.program_id,
            "program_name": program.program_name,
            "details": {
                "disciplines": [d["discipline"] for d in curriculum_data[:3]] + ["..."],
                "departments": list(set(d["department"] for d in curriculum_data)),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Критическая ошибка импорта: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


# def parse_excel_file_from_bytes(file_bytes: BytesIO):
#     """Парсинг Excel из BytesIO"""
#     try:
#         # Пытаемся определить формат файла
#         try:
#             # Сначала пробуем openpyxl для .xlsx
#             df_svod = pd.read_excel(
#                 file_bytes, sheet_name="ПланСвод", header=2, engine="openpyxl"
#             )
#             df_plan = pd.read_excel(
#                 file_bytes, sheet_name="План", header=2, engine="openpyxl"
#             )
#         except Exception as e:
#             # Если не получилось, пробуем xlrd для старых .xls
#             file_bytes.seek(0)  # Возвращаем указатель в начало
#             try:
#                 df_svod = pd.read_excel(
#                     file_bytes, sheet_name="ПланСвод", header=2, engine="xlrd"
#                 )
#                 df_plan = pd.read_excel(
#                     file_bytes, sheet_name="План", header=2, engine="xlrd"
#                 )
#             except Exception as e:
#                 raise ValueError(f"Не удалось прочитать файл как Excel: {str(e)}")

#         # Дальнейшая обработка данных
#         df_svod.columns = df_svod.columns.str.strip().str.lower()
#         df_plan.columns = df_plan.columns.str.strip().str.lower()

#         required_columns = {"наименование", "наименование.1"}
#         if not required_columns.issubset(df_svod.columns):
#             raise ValueError(f"Отсутствуют обязательные колонки: {required_columns}")

#         if "считать в плане" not in df_plan.columns:
#             raise ValueError("Отсутствует колонка 'считать в плане'")

#         # Подготовка данных
#         df_svod_clean = df_svod[["наименование", "наименование.1"]].copy()
#         df_svod_clean.columns = ["дисциплина", "кафедра"]
#         df_svod_clean = df_svod_clean.dropna(subset=["дисциплина"])
#         df_svod_clean["кафедра"] = df_svod_clean["кафедра"].fillna("Не указано")

#         df_plan = df_plan[df_plan["считать в плане"] != "-"]
#         df_plan = df_plan.rename(columns={"наименование": "дисциплина"})

#         # Объединение данных
#         df_combined = pd.merge(
#             df_svod_clean, df_plan, on="дисциплина", how="inner"
#         ).fillna(0)

#         return df_combined
#     except Exception as e:
#         raise ValueError(f"Ошибка парсинга Excel: {str(e)}")


def safe_convert(value, convert_func, default):
    try:
        # Проверка на строку 'nan'
        if str(value).strip().lower() == "nan":
            return default
        if pd.isna(value) or str(value).strip() in ("", "-", "н/д"):
            return default
        return convert_func(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Ошибка преобразования значения {value}: {e}")
        return default


def check_duplicates_in_csv(file_path: str):
    """
    Проверяет наличие дубликатов в столбце program_name в CSV-файле.
    """
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        program_names = set()
        duplicates = set()

        for row in reader:
            program_name = row["program_name"].strip()
            if program_name in program_names:
                duplicates.add(program_name)
            else:
                program_names.add(program_name)

        if duplicates:
            raise ValueError(f"Найдены дубликаты в CSV-файле: {', '.join(duplicates)}")


def remove_duplicates_from_csv(file_path: str, output_file_path: str):
    """
    Удаляет дубликаты из CSV-файла на основе поля program_name и сохраняет результат в новый файл.
    """
    try:
        with open(file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            unique_rows = {}

            for row in reader:
                program_name = row["program_name"].strip()
                # Если program_name уже есть, пропускаем запись
                if program_name not in unique_rows:
                    unique_rows[program_name] = row

        # Сохраняем уникальные записи в новый файл
        with open(
            output_file_path, mode="w", encoding="utf-8", newline=""
        ) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(unique_rows.values())

        print(
            f"Дубликаты удалены. Уникальные записи сохранены в файл: {output_file_path}"
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка при удалении дубликатов: {e}")


def import_education_programs(file_path: str, db: Session):
    """
    Импортирует образовательные программы из CSV-файла в таблицу education_programs.
    Если программа с таким program_name уже существует, она обновляется.
    """
    try:
        # Удаляем дубликаты перед импортом
        cleaned_file_path = "cleaned_" + file_path
        remove_duplicates_from_csv(file_path, cleaned_file_path)

        with open(cleaned_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                program_name = row["program_name"].strip()
                year = int(row["year"])

                # Генерация short_name из профиля в скобках
                profile_match = re.search(r"\((.*?)\)", program_name)
                profile = profile_match.group(1) if profile_match else "UNKNOWN"
                short_name = f"{program_name.split()[0]}_{''.join(word[0] for word in profile.split())}_{year}"

                # Проверяем уникальность short_name
                counter = 1
                base_short_name = short_name
                while (
                    db.query(EducationProgram).filter_by(short_name=short_name).first()
                ):
                    short_name = f"{base_short_name}_{counter}"
                    counter += 1

                # Проверяем, существует ли запись с таким program_name
                existing_program = (
                    db.query(EducationProgram)
                    .filter_by(program_name=program_name)
                    .first()
                )
                if existing_program:
                    # Обновляем существующую запись
                    existing_program.short_name = short_name
                    existing_program.year = year
                else:
                    # Добавляем новую запись
                    new_program = EducationProgram(
                        program_name=program_name, short_name=short_name, year=year
                    )
                    db.add(new_program)

            db.commit()
            print("Импорт завершен.")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Ошибка импорта образовательных программ: {e}")
