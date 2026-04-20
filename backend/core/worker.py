from celery import Celery
from core.config import settings

celery = Celery(
    "worker",
    broker=settings.redis_url,          
    backend=settings.celery_result_backend,
    include=[]
)

celery.conf.broker_connection_retry_on_startup = True