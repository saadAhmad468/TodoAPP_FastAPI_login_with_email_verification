from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import SessionLocal
from models import Todos
from routers import auth, todo, google_auth
from routers.auth import get_current_user
from routers import auth
app = FastAPI()

# Mount static files (e.g. CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(auth.router)
app.include_router(todo.router)
app.include_router(google_auth.router)

app.include_router(auth.router)

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123456789")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home route
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Traditional login form page
@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Traditional login POST handler
@app.post("/token")
async def login_for_token(
        request: Request,
        response: Response,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    from routers.auth import authenticate_user, create_access_token
    user = authenticate_user(username, password, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "msg": "Invalid credentials"})

    token = create_access_token(user.username, user.id, user.role)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

# Registration page
@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Dashboard page (Supports both Google session and traditional token)
@app.get("/dashboard")
async def dashboard(
        request: Request,
        db: Session = Depends(get_db)
):
    # Try getting Google OAuth session
    user = request.session.get("user")

    # If not Google user, fallback to traditional token
    if not user:
        try:
            user = get_current_user(request)
        except:
            return RedirectResponse(url="/login")

    todos = db.query(Todos).filter(Todos.owner_id == user["id"]).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "todos": todos})
