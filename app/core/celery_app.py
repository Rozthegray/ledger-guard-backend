import os
from celery import Celery
from ssl import CERT_REQUIRED

# Load Env Vars
BROKER_URL = os.getenv("CELERY_BROKER_URL")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND")

celery_app = Celery(
    "ledger_guard_worker",
    broker=BROKER_URL,
    backend=BACKEND_URL
)

# CRITICAL FOR UPSTASH:
# Upstash requires SSL (rediss://). Celery needs specific SSL settings to work with it.
celery_app.conf.update(
    broker_use_ssl={
        'ssl_cert_reqs': CERT_REQUIRED
    },
    redis_backend_use_ssl={
        'ssl_cert_reqs': CERT_REQUIRED
    },
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)