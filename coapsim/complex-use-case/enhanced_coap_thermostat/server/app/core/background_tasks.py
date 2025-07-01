# server/app/core/background_tasks.py
"""
Background task management for the Smart Thermostat API.
Extracted from the original main.py control loop and task management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import ServerConfig
    from ..services.thermostat_service import ThermostatControlService
    from ..services.prediction_service import PredictionService
    from ..services.maintenance_service import MaintenanceService
    from ..api.websocket_handler import WebSocketManager

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """
    Manages all background tasks for the Smart Thermostat system.
    
    This includes:
    - Control loop for thermostat management
    - Periodic predictions
    - Maintenance checks
    - Data cleanup tasks
    - Health monitoring
    """
    
    def __init__(
        self,
        config: 'ServerConfig',
        thermostat_service: 'ThermostatControlService',
        prediction_service: 'PredictionService',
        maintenance_service: 'MaintenanceService',
        websocket_manager: 'WebSocketManager'
    ):
        self.config = config
        self.thermostat_service = thermostat_service
        self.prediction_service = prediction_service
        self.maintenance_service = maintenance_service
        self.websocket_manager = websocket_manager
        
        # Task management
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.task_intervals = {
            'control_loop': 30,  # seconds
            'predictions': 300,  # 5 minutes
            'maintenance_check': 3600,  # 1 hour
            'data_cleanup': 86400,  # 24 hours
            'health_monitor': 60,  # 1 minute
        }
        
        # Task state tracking
        self.task_stats = {
            'control_loop': {'runs': 0, 'errors': 0, 'last_run': None, 'last_error': None},
            'predictions': {'runs': 0, 'errors': 0, 'last_run': None, 'last_error': None},
            'maintenance_check': {'runs': 0, 'errors': 0, 'last_run': None, 'last_error': None},
            'data_cleanup': {'runs': 0, 'errors': 0, 'last_run': None, 'last_error': None},
            'health_monitor': {'runs': 0, 'errors': 0, 'last_run': None, 'last_error': None},
        }
        
        logger.info("BackgroundTaskManager initialized")

    async def start_all_tasks(self):
        """Start all background tasks."""
        if self.running:
            logger.warning("Background tasks are already running")
            return
        
        self.running = True
        logger.info("Starting all background tasks...")
        
        try:
            # Start each background task
            self.tasks['control_loop'] = asyncio.create_task(
                self._run_periodic_task('control_loop', self._control_loop)
            )
            
            # self.tasks['predictions'] = asyncio.create_task(
            #     self._run_periodic_task('predictions', self._prediction_task)
            # )
            
            # self.tasks['maintenance_check'] = asyncio.create_task(
            #     self._run_periodic_task('maintenance_check', self._maintenance_task)
            # )
            
            self.tasks['data_cleanup'] = asyncio.create_task(
                self._run_periodic_task('data_cleanup', self._cleanup_task)
            )
            
            self.tasks['health_monitor'] = asyncio.create_task(
                self._run_periodic_task('health_monitor', self._health_monitor_task)
            )
            
            logger.info(f"✅ Started {len(self.tasks)} background tasks")
            
        except Exception as e:
            logger.error(f"❌ Failed to start background tasks: {e}", exc_info=True)
            await self.stop_all_tasks()
            raise

    async def stop_all_tasks(self):
        """Stop all background tasks gracefully."""
        if not self.running:
            logger.info("Background tasks are not running")
            return
        
        self.running = False
        logger.info("Stopping all background tasks...")
        
        try:
            # Cancel all tasks
            for task_name, task in self.tasks.items():
                if task and not task.done():
                    logger.info(f"Cancelling task: {task_name}")
                    task.cancel()
            
            # Wait for tasks to complete cancellation
            if self.tasks:
                completed_tasks = await asyncio.gather(
                    *self.tasks.values(), 
                    return_exceptions=True
                )
                
                # Log results
                for task_name, result in zip(self.tasks.keys(), completed_tasks):
                    if isinstance(result, asyncio.CancelledError):
                        logger.info(f"✅ Task {task_name} cancelled successfully")
                    elif isinstance(result, Exception):
                        logger.error(f"❌ Task {task_name} stopped with error: {result}")
                    else:
                        logger.info(f"✅ Task {task_name} completed normally")
            
            self.tasks.clear()
            logger.info("✅ All background tasks stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping background tasks: {e}", exc_info=True)

    async def _run_periodic_task(self, task_name: str, task_func):
        """Run a task periodically with error handling and statistics."""
        interval = self.task_intervals[task_name]
        logger.info(f"Starting periodic task '{task_name}' with {interval}s interval")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Run the task
                await task_func()
                
                # Update statistics
                self.task_stats[task_name]['runs'] += 1
                self.task_stats[task_name]['last_run'] = start_time.isoformat()
                
                logger.debug(f"Task '{task_name}' completed successfully")
                
            except asyncio.CancelledError:
                logger.info(f"Task '{task_name}' was cancelled")
                break
            except Exception as e:
                # Update error statistics
                self.task_stats[task_name]['errors'] += 1
                self.task_stats[task_name]['last_error'] = str(e)
                
                logger.error(f"Error in task '{task_name}': {e}", exc_info=True)
                
                # For critical tasks, notify via alert system
                if task_name in ['control_loop', 'health_monitor']:
                    try:
                        # Import here to avoid circular imports
                        notification_service = getattr(self.config, '_notification_service', None)
                        if notification_service:
                            await notification_service.send_alert(
                                alert_type="system_failure",
                                message=f"Background task '{task_name}' failed: {str(e)}",
                                data={"task": task_name, "error": str(e)}
                            )
                    except Exception as alert_error:
                        logger.error(f"Failed to send alert for task failure: {alert_error}")
            
            try:
                # Wait for next iteration
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info(f"Task '{task_name}' sleep interrupted")
                break

    # async def _control_loop(self):
    #     """
    #     Main control loop for thermostat management.
    #     This is the core logic extracted from your original main.py
    #     """
    #     try:
    #         # Get all active devices (you'll need to adapt this to your device discovery)
    #         devices = await self._get_active_devices()
            
    #         for device_id in devices:
    #             try:
    #                 # Get current status
    #                 status = await self.thermostat_service.get_device_status(device_id)
    #                 await self.thermostat_service.process_control_cycle()

    #                 if not status:
    #                     logger.warning(f"Could not get status for device {device_id}")
    #                     continue
                    
    #                 # Check if device needs control updates
    #                 needs_update = await self._check_device_needs_update(device_id, status)
                    
    #                 if needs_update:
    #                     # Apply control logic
    #                     await self._apply_control_logic(device_id, status)
                    
    #                 # Broadcast status via WebSocket
    #                 if self.websocket_manager:
    #                     await self.websocket_manager.broadcast({
    #                         "type": "device_status",
    #                         "device_id": device_id,
    #                         "status": status,
    #                         "timestamp": datetime.now().isoformat()
    #                     })
                
    #             except Exception as e:
    #                 logger.error(f"Error processing device {device_id} in control loop: {e}")
    #                 continue
            
    #     except Exception as e:
    #         logger.error(f"Error in control loop: {e}", exc_info=True)
    #         raise

    async def _control_loop(self):
        """
        Main control loop - this is your original main.py control_loop logic
        """
        try:
            logger.debug("Executing thermostat control cycle...")
            
            # This calls your existing process_control_cycle method
            await self.thermostat_service.process_control_cycle()
            
            # Get the last processed data for maintenance checks
            last_device_data = self.thermostat_service.get_last_processed_data()
            
            if last_device_data:
                # Check for predictive maintenance needs
                await self.maintenance_service.check_maintenance_needs(last_device_data)
            else:
                logger.warning("No recent device data available for maintenance check.")

            # Check if ML retraining is needed (from your original logic)
            retrain_interval_hours = getattr(self.config, 'ML_RETRAIN_INTERVAL_HOURS', 24)
            if (self.prediction_service.last_training is None or 
                (datetime.now() - self.prediction_service.last_training).total_seconds() / 3600 >= retrain_interval_hours):
                logger.info(f"Retraining interval reached ({retrain_interval_hours} hours). Initiating model retraining.")
                await self.prediction_service.retrain_models()
            
        except Exception as e:
            logger.error(f"Error in control loop: {e}", exc_info=True)
            raise

    async def _prediction_task(self):
        """Generate and update temperature predictions."""
        try:
            devices = await self._get_active_devices()
            
            for device_id in devices:
                try:
                    # Generate predictions using your prediction service
                    #predictions = await self.prediction_service.generate_predictions(device_id)
                    predictions = await self.prediction_service.get_predictions(device_id)
                    
                    if predictions:
                        # Store predictions (adapt to your storage method)
                        await self._store_predictions(device_id, predictions)
                        
                        # Broadcast predictions via WebSocket
                        if self.websocket_manager:
                            await self.websocket_manager.broadcast({
                                "type": "predictions_updated",
                                "device_id": device_id,
                                "predictions": predictions,
                                "timestamp": datetime.now().isoformat()
                            })
                
                except Exception as e:
                    logger.error(f"Error generating predictions for device {device_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in prediction task: {e}", exc_info=True)
            raise

    async def _maintenance_task(self):
        """Check maintenance status and schedule maintenance tasks."""
        try:
            devices = await self._get_active_devices()
            
            for device_id in devices:
                try:
                    # Check maintenance status
                    maintenance_status = await self.maintenance_service.check_maintenance_needs(device_id)
                    
                    if maintenance_status.get('needs_attention', False):
                        # Send maintenance alert
                        notification_service = getattr(self.config, '_notification_service', None)
                        if notification_service:
                            await notification_service.send_alert(
                                alert_type="maintenance_required",
                                message=f"Device {device_id} requires maintenance: {maintenance_status.get('reason', 'Unknown')}",
                                data={"device_id": device_id, "maintenance_status": maintenance_status}
                            )
                
                except Exception as e:
                    logger.error(f"Error checking maintenance for device {device_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in maintenance task: {e}", exc_info=True)
            raise

    async def _cleanup_task(self):
        """Clean up old data and perform housekeeping."""
        try:
            # Clean up old InfluxDB data (implement based on your retention policy)
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Clean up old logs, temporary files, etc.
            await self._cleanup_old_data(cutoff_date)
            
            logger.info("Data cleanup task completed successfully")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
            raise

    async def _health_monitor_task(self):
        """Monitor system health and send alerts if needed."""
        try:
            # Check database connections
            health_issues = []
            
            # Check services health
            services_to_check = [
                ('thermostat_service', self.thermostat_service),
                ('prediction_service', self.prediction_service),
                ('maintenance_service', self.maintenance_service),
            ]
            
            for service_name, service in services_to_check:
                if hasattr(service, 'health_check'):
                    try:
                        health = await service.health_check()
                        if not health.get('healthy', True):
                            health_issues.append(f"{service_name}: {health.get('error', 'Unknown issue')}")
                    except Exception as e:
                        health_issues.append(f"{service_name}: Health check failed - {str(e)}")
            
            # Send alerts if there are health issues
            if health_issues:
                notification_service = getattr(self.config, '_notification_service', None)
                if notification_service:
                    await notification_service.send_alert(
                        alert_type="system_failure",
                        message=f"System health issues detected: {'; '.join(health_issues)}",
                        data={"health_issues": health_issues}
                    )
            
        except Exception as e:
            logger.error(f"Error in health monitor task: {e}", exc_info=True)
            raise

    # Helper methods (you'll need to implement these based on your specific logic)
    
    async def _get_active_devices(self) -> list:
        """Get list of active device IDs. Implement based on your device discovery."""
        # This is a placeholder - implement based on your device management
        # For example, from CoAP discovery, database, or configuration
        return getattr(self.config, 'DEVICE_IDS', ['smart-thermostat-01'])

    async def _check_device_needs_update(self, device_id: str, status: dict) -> bool:
        """Check if device needs control updates."""
        # Implement your control logic here
        # This is where you'd check schedules, target temperatures, etc.
        return False  # Placeholder

    async def _apply_control_logic(self, device_id: str, status: dict):
        """Apply control logic to device."""
        # Implement your thermostat control logic here
        pass  # Placeholder

    async def _store_predictions(self, device_id: str, predictions: dict):
        """Store predictions in database."""
        # Implement prediction storage
        pass  # Placeholder

    async def _cleanup_old_data(self, cutoff_date: datetime):
        """Clean up old data from databases."""
        # Implement data cleanup logic
        pass  # Placeholder

    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        return {
            "running": self.running,
            "active_tasks": len([t for t in self.tasks.values() if t and not t.done()]),
            "task_intervals": self.task_intervals,
            "task_statistics": self.task_stats,
            "uptime": datetime.now().isoformat() if self.running else None
        }

    async def restart_task(self, task_name: str):
        """Restart a specific background task."""
        if task_name not in self.task_intervals:
            raise ValueError(f"Unknown task: {task_name}")
        
        # Cancel existing task
        if task_name in self.tasks:
            old_task = self.tasks[task_name]
            if old_task and not old_task.done():
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    pass
        
        # Start new task
        task_func_map = {
            'control_loop': self._control_loop,
            #'predictions': self._prediction_task,
            #'maintenance_check': self._maintenance_task,
            'data_cleanup': self._cleanup_task,
            'health_monitor': self._health_monitor_task,
        }
        
        self.tasks[task_name] = asyncio.create_task(
            self._run_periodic_task(task_name, task_func_map[task_name])
        )
        
        logger.info(f"Restarted background task: {task_name}")

    async def update_task_interval(self, task_name: str, new_interval: int):
        """Update the interval for a specific task."""
        if task_name not in self.task_intervals:
            raise ValueError(f"Unknown task: {task_name}")
        
        old_interval = self.task_intervals[task_name]
        self.task_intervals[task_name] = new_interval
        
        logger.info(f"Updated {task_name} interval from {old_interval}s to {new_interval}s")
        
        # Restart the task with new interval
        await self.restart_task(task_name)