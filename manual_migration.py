# manual_migration.py
from app.database import SessionLocal
from app.models import TaughtDiscipline, Curriculum, Teacher

def restore_links():
    db = SessionLocal()
    
    # Пример восстановления связей (адаптируйте под ваши данные)
    links_to_create = [
        {"teacher_id": 1, "curriculum_id": 129},  # Архитектура ПО
        {"teacher_id": 1, "curriculum_id": 145},  # ВКР
        {"teacher_id": 1, "curriculum_id": 142},  # Практика
        # Добавьте остальные связи
    ]
    
    for link in links_to_create:
        # Проверяем существование записи
        if not db.query(TaughtDiscipline).filter_by(**link).first():
            db.add(TaughtDiscipline(**link))
    
    db.commit()
    print(f"Добавлено {len(links_to_create)} связей")

if __name__ == "__main__":
    restore_links()