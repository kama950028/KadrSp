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
from fastapi import HTTPException, UploadFile, BackgroundTasks, logger
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import re
import os
from datetime import datetime
from typing import List, Dict
from app.models import Curriculum, EducationProgram
import logging

logger = logging.getLogger(__name__)

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
    Улучшенный импорт с автоматической привязкой к программам и дисциплинам.
    """
    for entry in teachers_data:
        try:
            # Начало транзакции
            db.begin()

            # Поиск или создание преподавателя
            teacher = db.query(Teacher).filter(
                func.lower(Teacher.full_name) == func.lower(entry["full_name"])
            ).first()

            if not teacher:
                teacher = Teacher(
                    full_name=entry["full_name"].strip(),
                    position=entry["position"],
                    education_level=entry["education_level"],
                    total_experience=entry.get("total_experience", 0),
                    teaching_experience=entry.get("teaching_experience", 0),
                    professional_experience=entry.get("professional_experience", 0),
                    academic_degree=entry.get("academic_degree"),
                    academic_title=entry.get("academic_title"),
                )
                db.add(teacher)
                db.flush()

            # Обработка образовательных программ
            programs = [p.strip() for p in entry.get("programs_raw", "").split(";") if p.strip()]
            
            for program_name in programs:
                program = db.query(EducationProgram).filter_by(program_name=program_name).first()
                if not program:
                    profile_match = re.search(r"\((.*?)\)", program_name)
                    profile = profile_match.group(1) if profile_match else "UNKNOWN"
                    
                    # Список исключаемых союзов
                    stop_words = {"и", "или", "a", "но"}
                    
                    # Формируем инициалы профиля, исключая союзы
                    profile_initials = "".join([
                        word[0].upper() 
                        for word in re.findall(r'\b\w+\b', profile)  # Разделяем на слова, игнорируя пунктуацию
                        if re.sub(r'[^\w]', '', word).lower() not in stop_words
                    ])
                    
                    # Формирование short_name
                    program_part = program_name.split()[0].upper()
                    short_name = f"{program_part}_{profile_initials}_2023"

                    # Проверка уникальности
                    counter = 1
                    base_short_name = short_name
                    while db.query(EducationProgram).filter_by(short_name=short_name).first():
                        short_name = f"{base_short_name}_{counter}"
                        counter += 1

                    program = EducationProgram(
                        program_name=program_name, 
                        short_name=short_name, 
                        year=2023
                    )
                    db.add(program)
                    db.commit()
                    db.flush()

                # Привязка преподавателя к программе
                if program not in teacher.programs:
                    teacher.programs.append(program)

            # Обработка дисциплин с привязкой к программам
            disciplines = [d.strip() for d in entry.get("disciplines_raw", "").split(";") if d.strip()]
            
            for discipline_name in disciplines:
                # Поиск или создание дисциплины для конкретной программы
                curriculum = db.query(Curriculum).filter(
                    Curriculum.discipline == discipline_name,
                    Curriculum.program_id == program.program_id
                ).first()
                
                if not curriculum:
                    curriculum = Curriculum(
                        discipline=discipline_name,
                        program_id=program.program_id,
                        department="Не указано"
                    )
                    db.add(curriculum)
                    db.commit()
                    db.flush()

                # Привязка преподавателя к дисциплине
                if not db.query(TaughtDiscipline).filter_by(
                    teacher_id=teacher.teacher_id,
                    curriculum_id=curriculum.curriculum_id
                ).first():
                    td = TaughtDiscipline(
                        teacher_id=teacher.teacher_id,
                        curriculum_id=curriculum.curriculum_id
                    )
                    db.add(td)
                    db.commit()
            print(f"Добавлен преподаватель: {teacher.full_name}")
            print(f"Привязка к программе: {program.program_name}, дисциплина: {discipline_name}")
            # Фиксация изменений
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка импорта преподавателя {entry['full_name']}: {str(e)}")
            continue


def import_teachers_with_disciplines(db: Session, teachers_data: list):
    """
    Импортирует преподавателей и связывает их с дисциплинами.
    """
    for entry in teachers_data:
        try:
            # Поиск или создание преподавателя
            teacher = db.query(Teacher).filter(
                func.lower(Teacher.full_name) == func.lower(entry["full_name"])
            ).first()

            if not teacher:
                teacher = Teacher(
                    full_name=entry["full_name"].strip(),
                    position=entry["position"],
                    education_level=entry["education_level"],
                    total_experience=entry.get("total_experience", 0),
                    teaching_experience=entry.get("teaching_experience", 0),
                    professional_experience=entry.get("professional_experience", 0),
                    academic_degree=entry.get("academic_degree"),
                    academic_title=entry.get("academic_title"),
                )
                db.add(teacher)
                db.flush()

            # Обработка дисциплин
            disciplines = [d.strip() for d in entry.get("disciplines_raw", "").split(";") if d.strip()]
            
            for discipline_name in disciplines:
                # Поиск дисциплины
                discipline = db.query(Curriculum).filter(
                    Curriculum.discipline.ilike(discipline_name)
                ).first()

                if discipline:
                    # Привязка преподавателя к дисциплине
                    if not db.query(TaughtDiscipline).filter_by(
                        teacher_id=teacher.teacher_id,
                        curriculum_id=discipline.curriculum_id
                    ).first():
                        link = TaughtDiscipline(
                            teacher_id=teacher.teacher_id,
                            curriculum_id=discipline.curriculum_id
                        )
                        db.add(link)
                        db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка импорта преподавателя {entry['full_name']}: {str(e)}")
            continue



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


def import_curriculum(
    file_path: str, filename: str, db: Session, background_tasks: BackgroundTasks
):
    """
    Улучшенная функция импорта учебного плана.
    Извлекает short_name и year из имени файла и добавляет их в таблицу education_programs.
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

        # Извлечение short_name и year из имени файла
        try:
            match = re.match(r"(.+?)_(\d{4})\.xlsx", filename)
            if not match:
                raise ValueError("Некорректное имя файла. Ожидается формат: КОД_ПРОФИЛЬ_ГОД.xlsx")
            short_name = match.group(1)  # Извлекаем часть до года
            year = int(match.group(2))  # Извлекаем год
            short_name = f"{short_name}_{year}"  # Добавляем год в short_name
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка извлечения short_name и year из имени файла: {str(e)}",
            )

        # Проверяем, существует ли программа с таким short_name
        program = db.query(EducationProgram).filter_by(short_name=short_name).first()
        if program:
            # Удаляем связанные данные, если программа уже существует
            db.query(Curriculum).filter_by(program_id=program.program_id).delete()
            db.query(TaughtDiscipline).filter(
                TaughtDiscipline.curriculum_id.in_(
                    db.query(Curriculum.curriculum_id).filter_by(program_id=program.program_id)
                )
            ).delete()
            db.commit()
            print(f"Старые данные для программы {short_name} удалены.")

        else:
            # Добавляем новую образовательную программу
            program = EducationProgram(
                program_name="",  # Оставляем пустым
                short_name=short_name,
                year=year,
            )
            db.add(program)
            db.commit()
            db.refresh(program)
            print(f"Добавлена новая образовательная программа: {short_name} ({year})")

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

        # Привязка данных к программе
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

from collections import defaultdict


def parse_semester(exam_value, test_value, diff_value):
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

    diff_sem = parse_value(diff_value)
    if diff_sem is not None:
        semesters.append(str(diff_sem))
    
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

        # Проверка существования файла
        if not os.path.exists(file_path):
            raise ValueError(f"Файл не найден: {file_path}")
        
        # Проверка формата файла
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            raise ValueError(f"Некорректный формат файла: {file_path}")

        # Чтение файла Excel
        try:
            xls = pd.ExcelFile(file_path)
            print(f"Листы в файле: {xls.sheet_names}")
        except ValueError as e:
            raise ValueError(f"Ошибка чтения файла Excel: {str(e)}")
        except Exception as e:
            raise ValueError(f"Неизвестная ошибка при чтении файла: {str(e)}")
        

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
            # print(f"col_name: {col_name} current_course: {current_course}")

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
            elif "крпа" in col_name.lower():
                course_blocks[current_course]["krpa_col"] = col
                
            

        print("\nОбнаруженные блоки курсов:")
        for course, blocks in course_blocks.items():
            print(f"{course}: {blocks}")

         # 4. Автопоиск колонок для семестров
        exam_col = next((col for col in df_plan.columns if "экза" in str(col).lower()), None)
        test_col = next((col for col in df_plan.columns if "зачет" in str(col).lower()), None)
        diff_col = next((col for col in df_plan.columns if "зачет с оц" in str(col).lower()), None)
        kr_rab_col = next((col for col in df_plan.columns if "кр" in str(col).lower().replace(" ", "")), None)
        
        if not kr_rab_col:
            raise ValueError("Столбец 'кр' не найден в df_plan")
        else:
            print(f"Найден столбец 'кр': {kr_rab_col}")
        

        if not exam_col or not test_col or not diff_col or not kr_rab_col:
            available_cols = ", ".join(df_plan.columns)
            raise ValueError(
                f"Не найдены колонки с экзаменами, зачетами и дифф. зачетами. Доступные колонки: {available_cols}"
            )

        print(f"Найдены колонки: Экзамен - '{exam_col}', Зачет - '{test_col}', Дифф. зачет - '{diff_col}', КР - '{kr_rab_col}'")

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
            diff_value = row.get(diff_col, None)
            semesters = parse_semester(exam_value, test_value, diff_value)

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
            final_work_hours = 0.0
            course_project_hours = 0.0


            for course, blocks in course_blocks.items():
                try:
                    kr_rab_col = blocks.get("kr_rab_col")
                    if kr_rab_col and hours_data is not None and kr_rab_col in hours_data:
                        kr_rab_value = hours_data[kr_rab_col]
                        course_project_hours = float(2.0) if pd.notna(kr_rab_value) and str(kr_rab_value).strip() else 0.0
                    else:
                        course_project_hours = 0.0
                    
                    
                    # Получение значения krpa_value из соответствующего столбца
                    vkr_col = blocks.get("krpa_col")
                    vkr_value = hours_data[vkr_col] if (vkr_col and hours_data is not None and vkr_col in hours_data) else 0.0
                    final_work_hours = float(vkr_value - 1.5) if pd.notna(vkr_value) else 0.0

                    
                    
                    krpa_col = blocks.get("krpa_col")
                    krpa_value = hours_data[krpa_col] if (krpa_col and hours_data is not None and krpa_col in hours_data) else 0.0
                    if "практика" in discipline.lower():    
                        # print(f"Значение 'КрПА' для дисциплины '{discipline}': {krpa_value}")
                        practice_hours += float(krpa_value) if pd.notna(krpa_value) else 0.0

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
                        if "практика" in discipline.lower():
                            # print(f"Условие сработало для дисциплины '{discipline}'. Значение КрПА: {krpa_value}")
                            practice_hours += float(krpa_value) if pd.notna(krpa_value) else 0.0
                            # print(f"Присвоено practice_hours: {practice_hours}")
                        else:
                            practice_hours += float(val) if pd.notna(val) else 0
                            # print(f"Присвоено practice_hours из practice_col: {practice_hours}")


                    if "exam_col" in blocks:
                        val = (
                            hours_data[blocks["exam_col"]]
                            if hours_data is not None
                            else 0
                        )
                        if "защита" in discipline.lower():
                            exam_hours = 0
                        else:
                            exam_hours = 2.35 if pd.notna(exam_value) and str(exam_value).strip() not in ["", "nan"] else 0.0

                    if "test_col" in blocks:
                        val = (
                            hours_data[blocks["test_col"]]
                            if hours_data is not None
                            else 0
                        )
                        test_hours = 0.25 if pd.notna(test_value) and str(test_value).strip() not in ["", "nan"] else 0.0

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
                "lab_hours": lab_hours,
                "exam_hours": exam_hours,
                "test_hours": test_hours,
                "final_work_hours": final_work_hours,
                "course_project_hours": course_project_hours,
                "total_practice_hours": lecture_hours + practice_hours + lab_hours + exam_hours + test_hours + final_work_hours + course_project_hours,
            }
            # if "защита" in discipline.lower():
            if course_project_hours > 0 :
                print(f"\nДисциплина: {discipline}")
                print(f"Кафедра: {department}")
                print(f"Часы: лекции={lecture_hours}, практики={practice_hours}, лабы={lab_hours}")
                print(f"Часы: экзамен={exam_hours}, зачет={test_hours}, ВКР ={final_work_hours}, КР ={course_project_hours}")
                print(f"Всего часов: {item['total_practice_hours']}")
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





# def link_teachers_to_disciplines(db: Session):
#     """
#     Сопоставляет преподавателей с дисциплинами на основе данных из столбца disciplines_raw.
#     """
#     teachers = db.query(Teacher).all()

#     # for teacher in teachers:
#     #     if not teacher.disciplines_raw:
#     #         print(f"Преподаватель {teacher.full_name} не имеет указанных дисциплин.")
#     #         continue

#         # Разделяем дисциплины из disciplines_raw
#         discipline_names = [d.strip() for d in teacher.disciplines_raw.split(";") if d.strip()]

#         for discipline_name in discipline_names:
#             # Ищем дисциплину в таблице Curriculum
#             discipline = db.query(Curriculum).filter(
#                 func.lower(Curriculum.discipline) == func.lower(discipline_name)
#             ).first()

#             if not discipline:
#                 print(f"Дисциплина '{discipline_name}' не найдена для преподавателя {teacher.full_name}.")
#                 continue

#             # Проверяем, есть ли уже связь в таблице TaughtDiscipline
#             if not db.query(TaughtDiscipline).filter_by(
#                 teacher_id=teacher.teacher_id,
#                 curriculum_id=discipline.curriculum_id
#             ).first():
#                 # Создаем связь
#                 link = TaughtDiscipline(
#                     teacher_id=teacher.teacher_id,
#                     curriculum_id=discipline.curriculum_id
#                 )
#                 db.add(link)
#                 db.commit()
#                 print(f"Связь добавлена: Преподаватель {teacher.full_name} -> Дисциплина {discipline.discipline}")
#             else:
#                 print(f"Связь уже существует: Преподаватель {teacher.full_name} -> Дисциплина {discipline.discipline}")