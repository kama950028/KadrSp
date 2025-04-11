
import pytest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.import_utils import parse_excel

def test_parse_excel():

    # Test with a valid file path
    file_path = '/Users/anatoliy/Documents/Proj_VS/KadrSp/09.04.04_АИС_ИИТ_2024.xlsx'
    result = parse_excel(file_path)
    assert isinstance(result, list)  # Assuming parse_excel returns a list of dictionaries

    


def test_import():
    a = 2
    b = 2
    assert a + b == 4


