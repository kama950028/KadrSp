import pytest
import os
import pandas as pd
import sys
from sqlalchemy.orm import Session
from app.models import Curriculum
from app.services.import_utils import parse_excel
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

# def test_parse_excel():

#     # Test with a valid file path
#     file_path = '/Users/anatoliy/Documents/Proj_VS/KadrSp/09.04.04_АИС_ИИТ_2024.xlsx'
#     result = parse_excel(file_path)
#     assert isinstance(result, list)  # Assuming parse_excel returns a list of dictionaries

@pytest.fixture
def test_file_path():
    # Укажите путь к тестовому Excel-файлу
    return os.path.abspath("ПЛАНЫ/test_09.04.04_АИС_ИИТ_2024.xlsx")

@pytest.fixture(scope="function")
def db_session():
    # Создаем тестовую базу данных в памяти
    engine = create_engine("postgresql://postgres:Poi369258147@localhost/mydb2")  # SQLite в памяти
    Base.metadata.create_all(engine)  # Создаем все таблицы
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session  # Передаем сессию в тест

    session.close()
    Base.metadata.drop_all(engine)  # Удаляем таблицы после теста

@pytest.fixture
def expected_data_from_excel(test_file_path):
    # Чтение данных из Excel-файла
    df = pd.read_excel(test_file_path, sheet_name="Лист1") 


    # Преобразование данных в формат, соответствующий структуре базы данных
    expected_data = []
    for _, row in df.iterrows():
        expected_data.append({
            "discipline": row["Дисциплина"],
            "department": row["Кафедра"],
            "semester": [int(s) for s in str(row["Семестр"]).split(",")] if pd.notna(row["Семестр"]) else None,
            "lecture_hours": float(row["Лекции (часы)"]) if pd.notna(row["Лекции (часы)"]) else 0.0,
            "practice_hours": float(row["Практика (часы)"]) if pd.notna(row["Практика (часы)"]) else 0.0,
            "lab_hours": float(row["Лабораторные (часы)"]) if pd.notna(row["Лабораторные (часы)"]) else 0.0,
            "exam_hours": float(row["Экзамен (часы)"]) if pd.notna(row["Экзамен (часы)"]) else 0.0,
            "test_hours": float(row["Зачет (часы)"]) if pd.notna(row["Зачет (часы)"]) else 0.0,
            "course_project_hours": float(row["Курсовой проект (часы)"]) if pd.notna(row["Курсовой проект (часы)"]) else 0.0,
            "final_work_hours": float(row["ВКР (часы)"]) if pd.notna(row["ВКР (часы)"]) else 0.0,
        })
    print("Ожидаемые данные из Excel:", expected_data)  # Отладочный вывод
    return expected_data

def test_compare_excel_with_db(test_file_path, expected_data_from_excel, db_session):
    # Добавляем тестовые данные в базу данных
    for data in expected_data_from_excel:
        db_session.add(Curriculum(**data))
    db_session.commit()

    # Тест сравнения данных из Excel с базой данных
    db_data = db_session.query(Curriculum).all()
    db_data_as_dict = [
        {
            "discipline": item.discipline,
            "department": item.department,
            "semester": item.semester,
            "lecture_hours": item.lecture_hours,
            "practice_hours": item.practice_hours,
            "lab_hours": item.lab_hours,
            "exam_hours": item.exam_hours,
            "test_hours": item.test_hours,
            "course_project_hours": item.course_project_hours,
            "final_work_hours": item.final_work_hours,
        }
        for item in db_data
    ]

    assert len(expected_data_from_excel) == len(db_data_as_dict), "Количество записей не совпадает"
    for i, expected_item in enumerate(expected_data_from_excel):
        assert expected_item == db_data_as_dict[i], f"Запись {i} не совпадает с ожидаемой"


def test_parse_excel(test_file_path, expected_data_from_excel):
    # Тест функции parse_excel
    result = parse_excel(test_file_path)
    print("Результат parse_excel:", result)  # Отладочный вывод
    assert isinstance(result, list), "Результат должен быть списком"
    assert len(result) == len(expected_data_from_excel), "Количество записей не совпадает"
    for i, item in enumerate(result):
        assert item == expected_data_from_excel[i], f"Запись {i} не совпадает с ожидаемой"

    


# def test_import():
#     a = 2
#     b = 2
#     assert a + b == 4


