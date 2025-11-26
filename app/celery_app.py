from celery import Celery

REDIS_HOST = 'redis://127.0.0.1:6379/0'

celery_app = Celery(
    "online_store",
    broker=REDIS_HOST,
    backend=REDIS_HOST,
    broker_connection_retry_on_startup=True
)

import app.tasks.email_tasks