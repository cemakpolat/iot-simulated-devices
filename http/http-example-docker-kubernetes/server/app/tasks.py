import logging
from celery_app import celery # <--- IMPORT FROM THE NEW FILE
from models import ModelRegistry
from database import insert_reading, delete_inactive_devices_from_db

logger = logging.getLogger(__name__)
# The model registry can be instantiated here, it's stateless.
model_registry = ModelRegistry()

@celery.task
def process_data_task(data):
    """Celery task to process incoming IoT data."""
    try:
        device_id = data['device_id']
        timestamp = data['timestamp']
        
        for metric in data.get('metrics', []):
            metric_type = metric.get('type')
            value = metric.get('value')
            
            model = model_registry.get_model(metric_type)
            if model:
                result, confidence = model.predict(value)
                logger.info(f"Processed: {device_id} - {metric_type} -> {result}")
                
                insert_reading(timestamp, device_id, metric_type, value, result, confidence)
            else:
                logger.warning(f"No model found for metric type: {metric_type}")

    except Exception as e:
        logger.error(f"Error processing task: {e}")


@celery.task
def cleanup_inactive_devices_task():
    """Celery beat task to delete old device data."""
    try:
        logger.info("Running scheduled task: cleanup_inactive_devices_task")
        rows_deleted = delete_inactive_devices_from_db()
        logger.info(f"Cleanup task complete. Deleted data for {rows_deleted} inactive device(s).")
    except Exception as e:
        logger.error(f"Error during cleanup task: {e}")