import aiosmtplib
from email.message import EmailMessage

async def send_email_async(recipient: str, subject: str, body: str):
    sender = "admin@email.com"
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(message,
        hostname="localhost",
        recipients=[recipient],
        sender=sender,
        port=1025,
    )
