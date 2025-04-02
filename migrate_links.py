# migrate_links.py
from app.database import SessionLocal
from app.models import TaughtDiscipline, Curriculum, Teacher
from sqlalchemy import or_

def migrate_links():
    db = SessionLocal()
    
    # Соответствие старых и новых curriculum_id по названиям дисциплин
    discipline_mapping = {
        "Архитектура, проектирование и разработка программных средств": 129,
        "Выполнение и защита выпускной квалификационной работы": 145,
        "Ознакомительная практика": 142,
        # Добавьте остальные соответствия
    }

    for old_name, new_id in discipline_mapping.items():
        # Находим старые связи для этой дисциплины
        old_links = db.query(TaughtDiscipline)\
            .join(Curriculum)\
            .filter(Curriculum.discipline == old_name)\
            .all()
        
        # Переносим связи на новый curriculum_id
        for link in old_links:
            if not db.query(TaughtDiscipline)\
                .filter_by(
                    teacher_id=link.teacher_id,
                    curriculum_id=new_id
                ).first():
                
                db.add(TaughtDiscipline(
                    teacher_id=link.teacher_id,
                    curriculum_id=new_id
                ))
    
    db.commit()
    print(f"Перенесено {len(old_links)} связей")

if __name__ == "__main__":
    migrate_links()