import logging
import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv

# Force load .env
load_dotenv()

# Setup Logging
logger = logging.getLogger("uvicorn")

#  1. ROBUST CONFIGURATION
# We remove defaults for username/password to ensure we fail loudly if .env is missing.
# This prevents the app from trying to connect with "user"/"password" and timing out.
#  UPDATED CONFIG FOR PORT 587 (SSL)

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "rozthegrey@gmail.com"),
    # CHANGE: Set default to 587, but allow .env to override it
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)), 
    MAIL_SERVER="smtp.gmail.com",
    
    # CHANGE: Enable STARTTLS (Required for Port 587)
    MAIL_STARTTLS=True,
    # CHANGE: Disable SSL (Required for Port 587)
    MAIL_SSL_TLS=False,
    
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_verification_email(email: EmailStr, code: str):
    """
    Sends a verification email using Google SMTP with robust error handling.
    """
    
    # 🟢 Dev Mode Fallback: Always print to console first
    print(f"\n{'='*40}")
    print(f"📧 [SMTP] Attempting to send to: {email}")
    print(f"🔑 CODE: {code}")
    print(f"{'='*40}\n")

    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #333;">Verify your Ledger Guard Account</h2>
        <p>Your verification code is:</p>
        <h1 style="color: #007bff; letter-spacing: 5px;">{code}</h1>
        <p style="font-size: 12px; color: #888;">If you did not request this, please ignore this email.</p>
    </div>
    """

    message = MessageSchema(
        subject="Your Ledger Guard Verification Code",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    try:
        # Check credentials exist before trying to connect
        if not conf.MAIL_USERNAME or not conf.MAIL_PASSWORD:
            raise ValueError("MAIL_USERNAME or MAIL_PASSWORD is missing in .env")

        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"✅ Email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"❌ SMTP Error: {str(e)}")
        # If it fails, we rely on the console print above so the user isn't stuck.
        return False

async def send_notification_email(email: EmailStr, task_name: str):
    """
    Sends a simple notification email when an audit is complete.
    """
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h3>Audit Completed</h3>
        <p>The audit for <b>{task_name}</b> has finished successfully.</p>
        <p>Log in to your dashboard to view the report.</p>
    </div>
    """

    message = MessageSchema(
        subject=f"Audit Complete: {task_name}",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    try:
        if conf.MAIL_USERNAME and conf.MAIL_PASSWORD:
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info(f"✅ Notification sent to {email}")
    except Exception as e:
        logger.error(f"❌ Failed to send notification: {e}")
