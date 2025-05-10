from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel  # 👈 Added for schema
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from models import User
from utils.token import create_email_token, verify_email_token
from utils.email import send_verification_email
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User
from utils.token import verify_email_token



class UserCreate(BaseModel):
    username: str
    password: str
    confirm_password: str
    role: str

router = APIRouter()
templates = Jinja2Templates(directory="templates")
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str, db):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta = timedelta(minutes=20)):
    encode = {"sub": username, "id": user_id, "role": role}
    expire = datetime.utcnow() + expires_delta
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_verification_token(email: str):
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

from fastapi import HTTPException

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub"), "id": payload.get("id"), "role": payload.get("role")}
    except JWTError:
        return RedirectResponse(url="/login")



@router.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, "msg": "Passwords do not match"})
    user = db.query(User).filter(User.username == username).first()
    if user:
        return templates.TemplateResponse("register.html", {"request": request, "msg": "Username already exists"})
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed_pw = bcrypt.hash(password)
    user = User(username=username, email=email, hashed_password=hashed_pw, is_active=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_email_token(email)
    send_verification_email(email, token)
    return templates.TemplateResponse("verify_email.html", {"request": request, "email": email})

@router.get("/auth/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    email = verify_email_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.username == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return RedirectResponse(url="/dashboard", status_code=302)

    user.is_active = True
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)



from fastapi.responses import HTMLResponse
from utils.token import create_email_token, verify_email_token
from utils.mail import send_email
from passlib.hash import bcrypt

@router.get("/auth/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/auth/forgot-password")
def send_reset_link(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("forgot_password.html", {"request": request, "msg": "Email not found"})

    token = create_email_token(email)
    subject = "Reset Your TaskGuard Password"
    link = f"http://localhost:8000/auth/reset-password?token={token}"
    body = f"Click to reset your password: {link}"
    send_email(to=email, subject=subject, body=body)
    return templates.TemplateResponse("verify_email.html", {"request": request, "email": email})

@router.get("/auth/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/auth/reset-password")
def reset_password(request: Request, token: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "msg": "Passwords do not match"})

    email = verify_email_token(token)
    if not email:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "msg": "Invalid or expired token"})

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "msg": "User not found"})

    user.hashed_password = bcrypt.hash(password)
    db.commit()
    return RedirectResponse(url="/login", status_code=302)
