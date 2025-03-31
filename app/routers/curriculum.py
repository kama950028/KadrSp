from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.models import Curriculum, EducationProgram
from app.database import get_db
from app.schemas import CurriculumBase
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

@router.get("/view", response_class=HTMLResponse)
def curriculum_view(request: Request):
    """
    Рендер страницы с выбором образовательной программы.
    """
    return templates.TemplateResponse("curriculum_view.html", {"request": request})

@router.get("/", response_model=List[CurriculumBase])
def get_curriculum(curriculum_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Получить список дисциплин учебных планов.
    Если указан `curriculum_id`, возвращает конкретную дисциплину учебного плана.
    """
    query = db.query(Curriculum).options(joinedload(Curriculum.program))
    
    if curriculum_id:
        curriculum = query.filter(Curriculum.curriculum_id == curriculum_id).first()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Учебный план не найден")
        return [curriculum]
    
    return query.all()



# @router.get("/EducationProgram")
# def get_education_programs(program_id: Optional[int] = None, db: Session = Depends(get_db)):
#     """
#     Получить список образовательных программ с их связанными дисциплинами и преподавателями.
#     Возвращает только те программы, у которых есть связанные дисциплины и преподаватели.
#     """
#     query = db.query(EducationProgram).options(
#         joinedload(EducationProgram.curriculum).joinedload(Curriculum.teachers)
#     )

#     if program_id:
#         program = query.filter(EducationProgram.program_id == program_id).first()
#         if not program:
#             raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
#         return program

#     # Фильтруем программы, у которых есть связанные дисциплины и преподаватели
#     programs = query.all()
#     filtered_programs = [
#         program for program in programs
#         if program.curriculum and any(curriculum.teachers for curriculum in program.curriculum)
#     ]

#     return filtered_programs



@router.get("/EducationProgram")
def get_education_programs(db: Session = Depends(get_db)):
    programs = db.query(EducationProgram).options(
        joinedload(EducationProgram.curriculum).joinedload(Curriculum.teachers)
    ).all()
    return programs