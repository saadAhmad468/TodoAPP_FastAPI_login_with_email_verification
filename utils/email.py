from utils.token import create_email_token
from utils.mail import send_email

def send_verification_email(email: str):
    token = create_email_token(email)
    verification_link = f"http://localhost:8000/auth/verify?token={token}"
    subject = "Verify your TaskGuard Account"
    body = f"Hi,\n\nPlease verify your email by clicking the link below:\n{verification_link}\n\nThanks!"
    send_email(to=email, subject=subject, body=body)