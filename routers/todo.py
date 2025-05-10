from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Todos
from routers.auth import get_current_user
from pydantic import BaseModel


class TodoCreate(BaseModel):
    title: str
    description: str

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/add")
async def add_todo(request: Request, title: str = Form(...), description: str = Form(...), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = Todos(title=title, description=description, owner_id=user["id"])
    db.add(todo)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/edit/{todo_id}")
async def edit_todo(todo_id: int, request: Request, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    return templates.TemplateResponse("edit.html", {"request": request, "todo": todo})

@router.post("/update/{todo_id}")
async def update_todo(todo_id: int, title: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    todo.title = title
    todo.description = description
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/delete/{todo_id}")
async def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    db.delete(todo)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)
