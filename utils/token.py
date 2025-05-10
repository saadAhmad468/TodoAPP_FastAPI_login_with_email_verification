from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "some-random-salt")

serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_email_token(email: str) -> str:
    return serializer.dumps(email, salt=SECURITY_PASSWORD_SALT)

def verify_email_token(token: str, expiration=3600) -> str | None:
    try:
        return serializer.loads(token, salt=SECURITY_PASSWORD_SALT, max_age=expiration)
    except Exception as e:
        print("Token verification error:", e)
        return None