# app/api/v1/notifications.py
from fastapi import APIRouter, Depends
from typing import Annotated

from ...core.dependencies import get_current_user, get_notification_service
from ...models.schemas import FCMTokenRequest, NotificationRequest, SuccessResponse
from ...models.database import User
from ...services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/register", response_model=SuccessResponse)
async def register_fcm_token(
    token_data: FCMTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)]
):
    """Register FCM token for push notifications."""
    success = await notification_service.register_token(
        token_data.token, 
        str(current_user.id)
    )
    return SuccessResponse(
        message="FCM token registered successfully" if success else "Token already registered"
    )

@router.post("/send", response_model=SuccessResponse)
async def send_notification(
    notification: NotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)]
):
    """Send test notification."""
    success = await notification_service.send_notification(
        notification.title,
        notification.body,
        notification.data
    )
    return SuccessResponse(
        message="Notification sent successfully" if success else "Failed to send notification"
    )

