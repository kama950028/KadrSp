import csv
from app.database import SessionLocal
from app.models import Teacher

def import_from_csv(file_path: str):
    db = SessionLocal()
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            teacher = Teacher(
                full_name=row['full_name'],
                position=row['position'],
                education_level=row['education_level']
            )
            db.add(teacher)
        
    db.commit()
    db.close()

if __name__ == "__main__":
    import_from_csv("teachers_data.csv")