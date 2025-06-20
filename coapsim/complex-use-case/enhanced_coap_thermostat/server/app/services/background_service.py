# app/services/background_service.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from .base import BaseService
from .device_service import DeviceService
from .ml_service import MLService
from .notification_service import NotificationService
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class BackgroundTaskManager(BaseService):
    """Manages all background tasks for the thermostat system."""
    
    def __init__(self):
        super().__init__()
        self.tasks: List[asyncio.Task] = []
        self.device_service: Optional[DeviceService] = None
        self.ml_service: Optional[MLService] = None
        self.notification_service: Optional[NotificationService] = None
        self.control_loop_interval = settings.POLL_INTERVAL
        self.running = False
    
    def set_services(self, device_service: DeviceService, ml_service: MLService, 
                    notification_service: NotificationService):
        """Set service dependencies."""
        self.device_service = device_service
        self.ml_service = ml_service
        self.notification_service = notification_service
    
    async def start(self):
        """Start all background tasks."""
        if self.running:
            self.logger.warning("Background tasks already running")
            return
        
        if not all([self.device_service, self.ml_service, self.notification_service]):
            raise RuntimeError("Services not properly configured")
        
        self.running = True
        self.logger.info("Starting background tasks...")
        
        # Create background tasks
        self.tasks = [
            asyncio.create_task(self._main_control_loop()),
            asyncio.create_task(self._ml_training_loop()),
            asyncio.create_task(self._health_monitoring_loop()),
            asyncio.create_task(self._cleanup_loop())
        ]
        
        self.logger.info(f"Started {len(self.tasks)} background tasks")
        return await super().initialize()
    
    async def stop(self):
        """Stop all background tasks."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping background tasks...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        await super().cleanup()
        self.logger.info("All background tasks stopped")
    
    async def _main_control_loop(self):
        """Main thermostat control loop."""
        consecutive_errors = 0
        max_errors = 5
        
        while self.running:
            try:
                # Get device status and sensor data
                device_id = "thermostat-01"  # This would come from device registry
                
                # Get current device status
                status = await self.device_service.get_device_status(device_id)
                sensor_data = await self.device_service.get_sensor_data(device_id)
                
                # Combine data for ML decision
                combined_data = {
                    "device_id": device_id,
                    "temperature": {"value": sensor_data.temperature},
                    "humidity": {"value": sensor_data.humidity},
                    "occupancy": sensor_data.occupancy,
                    "air_quality": sensor_data.air_quality,
                    "hvac_state": status.hvac_state,
                    "target_temperature": status.target_temperature
                }
                
                # Make AI decision
                decision = await self.ml_service.make_decision(combined_data)
                
                # Execute decision if confidence is high enough
                if decision.get("confidence", 0) > 0.3 and decision.get("action") != "off":
                    command = ThermostatCommand(
                        action=decision["action"],
                        target_temperature=decision.get("target_temperature"),
                        mode=decision.get("mode"),
                        fan_speed=decision.get("fan_speed")
                    )
                    
                    await self.device_service.send_command(device_id, command)
                    self.logger.info(f"Executed AI decision: {decision['action']} (confidence: {decision['confidence']:.2f})")
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # Wait for next cycle
                await asyncio.sleep(self.control_loop_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Control loop error ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    await self.notification_service.send_alert(
                        "system_failure",
                        f"Control loop failed {max_errors} times consecutively"
                    )
                    break
                
                # Wait longer after errors
                await asyncio.sleep(self.control_loop_interval * 2)
    
    async def _ml_training_loop(self):
        """Periodic ML model training loop."""
        while self.running:
            try:
                # Check if retraining is needed
                if await self.ml_service.should_retrain():
                    self.logger.info("Starting periodic ML model retraining...")
                    
                    success = await self.ml_service.retrain_models()
                    
                    if success:
                        self.logger.info("ML models retrained successfully")
                        await self.notification_service.send_alert(
                            "model_retrained",
                            "ML models have been successfully retrained"
                        )
                    else:
                        self.logger.warning("ML model retraining failed")
                        await self.notification_service.send_alert(
                            "model_training_failed",
                            "ML model retraining failed - manual intervention may be required"
                        )
                
                # Wait 1 hour before checking again
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"ML training loop error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _health_monitoring_loop(self):
        """System health monitoring loop."""
        while self.running:
            try:
                # Check system health
                health_data = await self._check_system_health()
                
                # Send alerts for critical issues
                if health_data.get("critical_issues"):
                    for issue in health_data["critical_issues"]:
                        await self.notification_service.send_alert(
                            "system_health",
                            f"Critical system issue detected: {issue}"
                        )
                
                # Check device connectivity
                try:
                    await self.device_service.get_device_status("thermostat-01")
                except Exception as e:
                    await self.notification_service.send_alert(
                        "device_offline",
                        f"Device connectivity issue: {str(e)}"
                    )
                
                # Wait 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def _cleanup_loop(self):
        """Periodic cleanup tasks."""
        while self.running:
            try:
                self.logger.debug("Running periodic cleanup tasks...")
                
                # Cleanup old notifications, logs, etc.
                # This could include:
                # - Removing old FCM tokens
                # - Cleaning up temporary files
                # - Archiving old data
                
                # Wait 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _check_system_health(self) -> dict:
        """Check overall system health."""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "critical_issues": [],
            "warnings": []
        }
        
        try:
            # Check memory usage, disk space, etc.
            # This is a simplified implementation
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                health_data["critical_issues"].append(f"High memory usage: {memory.percent}%")
            elif memory.percent > 80:
                health_data["warnings"].append(f"Memory usage: {memory.percent}%")
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                health_data["critical_issues"].append(f"Low disk space: {disk.percent}% used")
            elif disk.percent > 85:
                health_data["warnings"].append(f"Disk usage: {disk.percent}%")
            
        except ImportError:
            health_data["warnings"].append("psutil not available for system monitoring")
        except Exception as e:
            health_data["warnings"].append(f"Health check error: {str(e)}")
        
        return health_data