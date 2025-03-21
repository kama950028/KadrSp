from docx import Document
import csv

doc = Document('АИС МАГИ.docx')
table = doc.tables[0]

with open('output.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, delimiter=',')
    # Заголовки
    writer.writerow(["id", "full_name", "position", "disciplines", "education_level", "specialty", 
                    "academic_degree", "academic_title", "qualification_updates", 
                    "total_experience", "speciality_experience", "educational_programs"])
    # Данные
    for row in table.rows[1:]:  # Пропустить заголовок
        cells = [cell.text.strip().replace('\n', '; ') for cell in row.cells]
        writer.writerow(cells)