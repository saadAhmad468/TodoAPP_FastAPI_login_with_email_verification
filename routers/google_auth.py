from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from auth_config import oauth
from database import SessionLocal
from models import User
from utils.email import send_verification_email

router = APIRouter()

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/login/google")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        scope="openid email profile"
    )

@router.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
    user_info = user_info.json()

    email = user_info.get("email")
    print("User logged in with email:", email)

    # ✅ Try fetching by email or username to avoid duplicates
    user = db.query(User).filter((User.email == email) | (User.username == email)).first()

    if not user:
        new_user = User(
            username=email,
            email=email,
            role="user",
            is_active=False
        )
        db.add(new_user)
        try:
            db.commit()
            db.refresh(new_user)
            user = new_user
            try:
                send_verification_email(email)
            except Exception as e:
                print("Error sending verification email:", e)
        except Exception as e:
            db.rollback()
            print("Error creating user:", e)
            raise HTTPException(status_code=500, detail="Could not create user")

    elif not user.is_active:
        try:
            send_verification_email(email)
        except Exception as e:
            print("Error resending verification email:", e)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Please verify your email before accessing the dashboard.")

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "role": user.role
    }

    return RedirectResponse(url="/dashboard")
