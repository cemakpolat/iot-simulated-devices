import os
from celery import Celery
from config import Config # Import our config

# Create the Celery instance. This is the shared object.
celery = Celery(
    __name__,
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=['tasks']
)

# Celery Beat Configuration using the default scheduler
celery.conf.beat_schedule = {
    'cleanup-inactive-devices-every-minute': {
        'task': 'tasks.cleanup_inactive_devices_task',
        'schedule': 60.0, # Run every 60 seconds
    },
}
celery.conf.timezone = 'UTC'

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json'
)