import aiosmtplib
from email.message import EmailMessage
from app.config import settings

async def send_email_async(recipient: str, subject: str, body: str):
    """
    Отправляет email асинхронно через SMTP.
    """
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
    )