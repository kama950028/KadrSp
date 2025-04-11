import docx
import csv
import re

def generate_short_name(program_name, year):
    """
    Формирует short_name: Код_Профиль_Год.
    Исключает союзы (например, "и", "или") из профиля.
    """
    match = re.match(r"(\d{2}\.\d{2}\.\d{2}) (.+?) \((.+)\)", program_name)
    if match:
        code = match.group(1)  # Код программы
        profile = match.group(3)  # Профиль программы

        # Исключаем союзы
        stop_words = {"и", "или", "a", "но"}
        profile_words = [word for word in profile.split() if word.lower() not in stop_words]

        # Берём первые буквы каждого слова
        profile_initials = "".join(word[0].upper() for word in profile_words)
        short_name = f"{code}_{profile_initials}_{year}"
        return short_name

    print(f"Не удалось сформировать short_name для: {program_name}")  # Отладочный вывод
    return "Unknown"

def process_docx(file_path):
    # Извлекаем год из названия файла
    file_name = file_path.split("/")[-1]
    year_match = re.search(r'\d{4}', file_name)
    year = year_match.group(0) if year_match else "Unknown"

    # Открываем .docx файл
    doc = docx.Document(file_path)
    data = set()  # Используем множество для хранения уникальных записей

    # Ищем таблицы в документе
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if "Наименование образовательных программ" in cell.text:
                    # Обрабатываем строки таблицы
                    for row in table.rows[1:]:  # Пропускаем заголовок
                        # Отладочный вывод всех ячеек строки
                        row_data = [cell.text.strip() for cell in row.cells]
                        print(f"Данные строки: {row_data}")

                        # Извлекаем данные из последнего столбца
                        program_name = row.cells[-1].text.strip()
                        print(f"Обрабатываемая строка: {program_name}")  # Отладочный вывод
                        if program_name:
                            # Разделяем программы по ";"
                            programs = program_name.split(";")
                            for program in programs:
                                program = program.strip()
                                short_name = generate_short_name(program, year)
                                # Добавляем уникальную запись в множество
                                data.add((program, short_name, year))
                    break

    # Сохраняем результат в CSV
    output_file = f"processed_programs_{year}.csv"
    save_to_csv(data, output_file)
    print(f"Данные сохранены в файл: {output_file}")

def save_to_csv(data, output_file):
    # Сортируем данные по program_name
    sorted_data = sorted(data, key=lambda x: x[0])  # Сортировка по первому элементу (program_name)

    # Сохраняем данные в CSV файл
    with open(output_file, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)  # Убираем лишние кавычки
        writer.writerow(["program_name", "short_name", "year"])  # Заголовки
        writer.writerows(sorted_data)  # Уникальные строки

# Пример вызова функции
file_path = "/Users/anatoliy/Documents/Proj_VS/KadrSp/АИС_МАГИ_2023.docx"
process_docx(file_path)