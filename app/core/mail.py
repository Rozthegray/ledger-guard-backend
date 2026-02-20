import logging
import os
from pydantic import EmailStr
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Force load .env
load_dotenv()

# Setup Logging
logger = logging.getLogger("uvicorn")

# 🟢 SENDGRID CONFIGURATION
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("MAIL_FROM", "rozthegrey@gmail.com") 

async def send_verification_email(email: EmailStr, code: str):
    """
    Sends a verification email using the SendGrid API.
    """
    
    # 🟢 Console Log for Debugging
    print(f"\n{'='*40}")
    print(f"📧 [SendGrid] Attempting to send to: {email}")
    print(f"🔑 CODE: {code}")
    print(f"{'='*40}\n")

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #333;">Verify your Ledger Guard Account</h2>
        <p>Your verification code is:</p>
        <h1 style="color: #007bff; letter-spacing: 5px;">{code}</h1>
        <p style="font-size: 12px; color: #888;">If you did not request this, please ignore this email.</p>
    </div>
    """

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=email,
        subject="Your Ledger Guard Verification Code",
        html_content=html_content
    )

    try:
        if not SENDGRID_API_KEY:
            raise ValueError("SENDGRID_API_KEY is missing in Render Environment")

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✅ Email sent to {email}. Status: {response.status_code}")
        return True

    except Exception as e:
        logger.error(f"❌ SendGrid Error: {str(e)}")
        return False

async def send_notification_email(email: EmailStr, task_name: str):
    """
    Sends a simple notification email when an audit is complete via SendGrid.
    """
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h3>Audit Completed</h3>
        <p>The audit for <b>{task_name}</b> has finished successfully.</p>
        <p>Log in to your dashboard to view the report.</p>
    </div>
    """

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=email,
        subject=f"Audit Complete: {task_name}",
        html_content=html_content
    )

    try:
        if SENDGRID_API_KEY:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
            logger.info(f"✅ Notification sent to {email}")
    except Exception as e:
        logger.error(f"❌ Failed to send notification: {e}")
