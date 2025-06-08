# mobile/push_notifications.py
import asyncio
import logging
from typing import Dict, List, Any, Optional
import os

# To use Firebase Admin SDK, you need to install 'firebase-admin' and
# provide a service account key JSON file (e.g., certs/firebase-service-account.json)
# You would get this from your Firebase project settings.
# Uncomment the following lines if you configure Firebase.
# import firebase_admin
# from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

class PushNotificationService:
    """
    Handles sending push notifications to mobile devices using Firebase Cloud Messaging (FCM).
    Currently, this is a placeholder with mock registration and a disabled FCM client.
    """
    def __init__(self):
        self.fcm_initialized = False
        self.firebase_credential_path = os.getenv("FIREBASE_CREDENTIAL_PATH", "certs/firebase-service-account.json")
        
        # --- Firebase Initialization (Uncomment if you set up FCM) ---
        # if os.path.exists(self.firebase_credential_path):
        #     try:
        #         cred = credentials.Certificate(self.firebase_credential_path)
        #         firebase_admin.initialize_app(cred)
        #         self.fcm_initialized = True
        #         logger.info("Firebase Admin SDK initialized successfully for FCM.")
        #     except Exception as e:
        #         logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        # else:
        #     logger.warning(f"Firebase service account key not found at {self.firebase_credential_path}. Push notifications will be disabled.")

        # In a real app, `registered_devices` would be persisted in a database (e.g., PostgreSQL)
        self.registered_devices: Dict[str, List[Dict[str, str]]] = {} # {user_id: [{device_token: "...", platform: "..."}]}
        logger.info("PushNotificationService initialized (FCM currently disabled).")

    async def register_device(self, user_id: str, device_token: str, platform: str) -> bool:
        """
        Registers a mobile device token for a specific user.
        In a real app, this data would be stored in a persistent database.
        """
        if not device_token or not platform:
            logger.warning(f"Attempted to register device with missing token or platform for user {user_id}.")
            return False

        if user_id not in self.registered_devices:
            self.registered_devices[user_id] = []
        
        # Avoid duplicate tokens for the same user
        if not any(d['device_token'] == device_token for d in self.registered_devices[user_id]):
            self.registered_devices[user_id].append({"device_token": device_token, "platform": platform})
            logger.info(f"Device token {device_token[:10]}... registered for user {user_id} on {platform}.")
            # Production: Save to a persistent database (e.g., PostgreSQL `models.py`)
            return True
        logger.info(f"Device token {device_token[:10]}... already registered for user {user_id}.")
        return False

    async def unregister_device(self, user_id: str, device_token: str) -> bool:
        """
        Unregisters a mobile device token for a specific user.
        """
        if user_id in self.registered_devices:
            original_len = len(self.registered_devices[user_id])
            self.registered_devices[user_id] = [
                d for d in self.registered_devices[user_id] if d['device_token'] != device_token
            ]
            if len(self.registered_devices[user_id]) < original_len:
                logger.info(f"Device token {device_token[:10]}... unregistered for user {user_id}.")
                # Production: Remove from persistent database
                return True
        logger.info(f"Device token {device_token[:10]}... not found for user {user_id}.")
        return False

    async def send_notification(self, user_id: str, title: str, body: str, data: Dict[str, str] = None) -> bool:
        """
        Sends a push notification to all devices registered for a specific user via FCM.
        This method is currently a mock/placeholder until FCM is fully configured.
        """
        if not self.fcm_initialized:
            logger.warning("FCM not initialized. Cannot send push notifications. Simulating success.")
            # For testing, simulate success if FCM is not configured
            return True 

        # --- FCM Sending Logic (Uncomment if you set up FCM) ---
        # if user_id not in self.registered_devices or not self.registered_devices[user_id]:
        #     logger.info(f"No registered devices found for user {user_id}. Skipping FCM send.")
        #     return False

        # messages_to_send = []
        # for device_info in self.registered_devices[user_id]:
        #     token = device_info['device_token']
        #     message = messaging.Message(
        #         notification=messaging.Notification(title=title, body=body),
        #         data=data,
        #         token=token,
        #     )
        #     messages_to_send.append(message)
        
        # try:
        #     # Send all messages in a batch
        #     # messaging.send_all is blocking, so run in a separate thread to not block asyncio loop
        #     batch_response = await asyncio.to_thread(messaging.send_all, messages_to_send)
            
        #     success_count = batch_response.success_count
        #     failure_count = batch_response.failure_count
            
        #     logger.info(f"Sent {success_count} FCM notifications to user {user_id}. Failed: {failure_count}.")
            
        #     if failure_count > 0:
        #         for i, resp in enumerate(batch_response.responses):
        #             if not resp.success:
        #                 logger.error(f"Failed to send message to {messages_to_send[i].token[:10]}...: {resp.exception}")
        #                 # If token is unregistered, remove it from our stored devices
        #                 if resp.exception and messaging.IsMessagingError(resp.exception) and resp.exception.code == "messaging/registration-token-not-registered":
        #                     logger.warning(f"Removing invalid FCM token: {messages_to_send[i].token[:10]}...")
        #                     asyncio.create_task(self.unregister_device(user_id, messages_to_send[i].token))
        #     return success_count > 0
        # except Exception as e:
        #     logger.error(f"Error sending FCM notifications to user {user_id}: {e}", exc_info=True)
        #     return False
        
        # If FCM is not initialized, we just return True for now for simulated success.
        return True # Placeholder: assume success if FCM is not active for testing purposes