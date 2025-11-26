import asyncio
from app.celery_app import celery_app
from app.email_service.send_email import send_email_async

@celery_app.task
def send_email_task(to: str, subject: str, body: str):
    asyncio.run(send_email_async(to, subject, body))