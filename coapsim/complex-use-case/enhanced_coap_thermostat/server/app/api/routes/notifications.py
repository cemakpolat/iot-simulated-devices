# server/app/api/routes/notifications.py
"""Updated notification routes using the refactored NotificationService"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ..dependencies import get_notification_service
from ..models.requests import FCMTokenRequest, TestNotificationRequest, FCMUnregisterRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/fcm/register")
async def register_fcm_token(
    request: FCMTokenRequest,
    notification_service=Depends(get_notification_service)
):
    """Register FCM token using the refactored notification service"""
    try:
        user_info = {
            "username": request.username,
            "userId": request.userId,
            "email": request.email,
            "platform": request.platform,
            "registeredAt": request.timestamp or datetime.now().isoformat()
        }
        
        # Use the delegated FCM methods from notification service
        is_new = await notification_service.add_fcm_token(request.token, user_info)
        stats = await notification_service.get_fcm_token_statistics()
        
        return {
            "success": True,
            "message": f"Token {'registered' if is_new else 'updated'} successfully",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Failed to register FCM token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register token: {str(e)}")


@router.post("/fcm/unregister")
async def unregister_fcm_token(
    request: FCMUnregisterRequest,
    notification_service=Depends(get_notification_service)
):
    """Unregister FCM token using the refactored notification service"""
    try:
        logger.info(f"FCM token unregistration request: User={request.userId}, Token={request.token[:20]}...")
        
        # Use the delegated FCM method from notification service
        success = await notification_service.remove_fcm_token(request.token)

        # Get current statistics
        stats = await notification_service.get_fcm_token_statistics()
        
        return {
            "success": True,
            "message": "Token unregistered successfully" if success else "Token not found (may have been already removed)",
            "removed": success,
            "statistics": stats
        }
            
    except Exception as e:
        logger.error(f"❌ Error unregistering FCM token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to unregister token: {str(e)}")


@router.post("/fcm/test")
async def send_test_notification(
    request: TestNotificationRequest,
    notification_service=Depends(get_notification_service)
):
    """Send test FCM notification using the refactored notification service"""
    try:
        # Use the notification service's send_alert method
        await notification_service.send_alert(
            alert_type="test_notification",
            message=request.body,
            data={"title": request.title, "test": True}
        )
        
        return {"success": True, "message": "Test notification sent"}
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fcm/health")
async def fcm_health_check(
    notification_service=Depends(get_notification_service)
):
    """FCM health check using the refactored notification service"""
    try:
        stats = await notification_service.get_fcm_token_statistics()
        
        # Check if Firebase is initialized
        firebase_initialized = False
        try:
            import firebase_admin
            firebase_initialized = len(firebase_admin._apps) > 0
        except ImportError:
            pass
        
        # Check if FCM notifier is available and properly configured
        fcm_configured = notification_service.fcm_notifier is not None
        fcm_enabled = fcm_configured and notification_service.fcm_notifier.is_enabled()
        
        # Get last validation time if available
        last_validation = None
        if notification_service.fcm_notifier and hasattr(notification_service.fcm_notifier.fcm_token_manager, 'last_validation'):
            last_validation_obj = notification_service.fcm_notifier.fcm_token_manager.last_validation
            last_validation = last_validation_obj.isoformat() if last_validation_obj else None
        
        return {
            "status": "FCM service running" if fcm_enabled else "FCM service not configured",
            "timestamp": datetime.now().isoformat(),
            "firebase_initialized": firebase_initialized,
            "fcm_configured": fcm_configured,
            "fcm_enabled": fcm_enabled,
            "statistics": stats,
            "last_validation": last_validation
        }
    except Exception as e:
        logger.error(f"FCM health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="FCM service unavailable")


@router.post("/fcm/validate-tokens")
async def validate_tokens(
    force: bool = False,
    notification_service=Depends(get_notification_service)
):
    """Validate FCM tokens using the refactored notification service"""
    try:
        # Use the delegated FCM validation method
        await notification_service.validate_fcm_tokens(force=force)
        stats = await notification_service.get_fcm_token_statistics()
        
        return {
            "success": True,
            "message": "Token validation completed",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error validating FCM tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate tokens: {str(e)}")


@router.get("/fcm/tokens")
async def get_fcm_tokens_info(
    notification_service=Depends(get_notification_service)
):
    """Get detailed FCM token information"""
    try:
        token_info = await notification_service.get_fcm_token_info()
        stats = await notification_service.get_fcm_token_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "tokens": token_info
        }
    except Exception as e:
        logger.error(f"Error retrieving FCM token info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve token info: {str(e)}")


@router.delete("/fcm/tokens/cleanup")
async def cleanup_old_tokens(
    max_age_days: int = 30,
    notification_service=Depends(get_notification_service)
):
    """Cleanup old FCM tokens"""
    try:
        if notification_service.fcm_notifier:
            await notification_service.fcm_notifier.cleanup_old_tokens(max_age_days)
            stats = await notification_service.get_fcm_token_statistics()
            
            return {
                "success": True,
                "message": f"Cleaned up tokens older than {max_age_days} days",
                "statistics": stats
            }
        else:
            raise HTTPException(status_code=503, detail="FCM service not configured")
            
    except Exception as e:
        logger.error(f"Error cleaning up FCM tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cleanup tokens: {str(e)}")


@router.post("/test-alert")
async def send_test_alert(
    alert_type: str = "test_notification",
    message: str = "This is a test alert from the Smart Thermostat system",
    notification_service=Depends(get_notification_service)
):
    """Send a test alert through all configured notification channels"""
    try:
        await notification_service.send_alert(
            alert_type=alert_type,
            message=message,
            data={
                "test": True,
                "source": "api_test",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "success": True,
            "message": "Test alert sent through all configured notification channels"
        }
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")


@router.get("/status")
async def get_notification_status(
    notification_service=Depends(get_notification_service)
):
    """Get overall notification service status"""
    try:
        # Get status from all notifiers
        notifier_status = []
        for notifier in notification_service.notifiers:
            if hasattr(notifier, 'get_status'):
                status = notifier.get_status()
            else:
                status = {
                    "name": notifier.__class__.__name__,
                    "enabled": getattr(notifier, 'enabled', True)
                }
            notifier_status.append(status)
        
        # Get FCM specific statistics if available
        fcm_stats = await notification_service.get_fcm_token_statistics()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "notifiers": notifier_status,
            "fcm_statistics": fcm_stats,
            "total_notifiers": len(notification_service.notifiers)
        }
    except Exception as e:
        logger.error(f"Error getting notification status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get notification status: {str(e)}")


@router.post("/websocket/test")
async def send_websocket_test(
    message: str = "Test WebSocket notification",
    notification_service=Depends(get_notification_service)
):
    """Send a test WebSocket notification"""
    try:
        if notification_service.websocket_notifier:
            success = await notification_service.websocket_notifier.send(
                alert_type="websocket_test",
                message=message,
                data={"test": True, "timestamp": datetime.now().isoformat()}
            )
            
            return {
                "success": success,
                "message": "WebSocket test notification sent" if success else "No WebSocket connections available"
            }
        else:
            raise HTTPException(status_code=503, detail="WebSocket notifier not configured")
            
    except Exception as e:
        logger.error(f"Failed to send WebSocket test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send WebSocket test: {str(e)}")
    
router.add_api_route("/fcm/register", register_fcm_token, methods=["POST"])
router.add_api_route("/fcm/unregister", unregister_fcm_token, methods=["POST"])
router.add_api_route("/fcm/test", send_test_notification, methods=["POST"])
router.add_api_route("/fcm/health", fcm_health_check, methods=["GET"])
router.add_api_route("/fcm/validate-tokens", validate_tokens, methods=["POST"])
router.add_api_route("/fcm/tokens", get_fcm_tokens_info, methods=["GET"])
router.add_api_route("/fcm/cleanup", cleanup_old_tokens, methods=["DELETE"])
router.add_api_route("/test-alert", send_test_alert, methods=["POST"])
router.add_api_route("/status", get_notification_status, methods=["GET"])
router.add_api_route("/websocket/test", send_websocket_test, methods=["POST"])


