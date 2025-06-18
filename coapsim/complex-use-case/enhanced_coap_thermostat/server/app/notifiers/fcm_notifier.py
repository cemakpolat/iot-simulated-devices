# from datetime import datetime, timedelta
# import asyncio
# import os
# import logging
# from ..config import ServerConfig
# from typing import Dict, Any, TYPE_CHECKING, List, Set
# import firebase_admin
# from firebase_admin import credentials, messaging
# from firebase_admin.exceptions import FirebaseError
# logger = logging.getLogger(__name__)

# class FCMTokenManager:
#     """Enhanced FCM token manager with validation and cleanup"""
#     def __init__(self):
#         self.tokens: List[Dict[str, Any]] = []  # Store token info with metadata
#         self._lock = asyncio.Lock()
#         self.invalid_tokens: Set[str] = set()  # Track invalid tokens
    
#     async def add_token(self, token: str, user_info: Dict[str, Any] = None):
#         """Add a token with metadata"""
#         async with self._lock:
#             # Check if token already exists
#             existing_token = next((t for t in self.tokens if t["token"] == token), None)
#             if existing_token:
#                 # Update existing token info
#                 existing_token.update({
#                     "last_seen": datetime.now().isoformat(),
#                     "user_info": user_info or {}
#                 })
#                 logger.info(f"FCM token updated: {token[:20]}...")
#                 return False
            
#             # Add new token
#             token_info = {
#                 "token": token,
#                 "added_at": datetime.now().isoformat(),
#                 "last_seen": datetime.now().isoformat(),
#                 "user_info": user_info or {},
#                 "failed_attempts": 0
#             }
#             self.tokens.append(token_info)
#             logger.info(f"FCM token registered: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
#             return True
    
#     async def remove_token(self, token: str):
#         """Remove a specific token"""
#         async with self._lock:
#             initial_count = len(self.tokens)
#             self.tokens = [t for t in self.tokens if t["token"] != token]
#             self.invalid_tokens.discard(token)
#             removed = len(self.tokens) < initial_count
#             if removed:
#                 logger.info(f"FCM token removed: {token[:20]}...")
#             return removed
    
#     async def mark_token_invalid(self, token: str, error_message: str = ""):
#         """Mark a token as invalid and increment failure count"""
#         async with self._lock:
#             self.invalid_tokens.add(token)
            
#             # Find and update the token info
#             for token_info in self.tokens:
#                 if token_info["token"] == token:
#                     token_info["failed_attempts"] = token_info.get("failed_attempts", 0) + 1
#                     token_info["last_error"] = error_message
#                     token_info["last_error_at"] = datetime.now().isoformat()
                    
#                     # Remove token if it has failed too many times
#                     if token_info["failed_attempts"] >= 3:
#                         logger.warning(f"Removing FCM token after {token_info['failed_attempts']} failures: {token[:20]}...")
#                         await self.remove_token(token)
#                         return True
#                     break
            
#             logger.warning(f"FCM token marked as invalid: {token[:20]}... - {error_message}")
#             return False
    
#     async def get_valid_tokens(self) -> List[str]:
#         """Get list of valid tokens only"""
#         async with self._lock:
#             valid_tokens = []
#             for token_info in self.tokens:
#                 if token_info["token"] not in self.invalid_tokens:
#                     valid_tokens.append(token_info["token"])
#             return valid_tokens
    
#     async def get_tokens(self) -> List[str]:
#         """Get all tokens (for backward compatibility)"""
#         return await self.get_valid_tokens()
    
#     async def get_token_info(self) -> List[Dict[str, Any]]:
#         """Get detailed token information"""
#         async with self._lock:
#             return [
#                 {
#                     "token": t["token"][:20] + "...",
#                     "added_at": t["added_at"],
#                     "last_seen": t["last_seen"],
#                     "user_info": t["user_info"],
#                     "failed_attempts": t.get("failed_attempts", 0),
#                     "is_valid": t["token"] not in self.invalid_tokens
#                 }
#                 for t in self.tokens
#             ]
    
#     async def cleanup_old_tokens(self, max_age_days: int = 30):
#         """Remove tokens older than specified days"""
#         async with self._lock:
#             cutoff_date = datetime.now() - timedelta(days=max_age_days)
#             initial_count = len(self.tokens)
            
#             self.tokens = [
#                 t for t in self.tokens 
#                 if datetime.fromisoformat(t["added_at"].replace('Z', '+00:00')) > cutoff_date
#             ]
            
#             removed_count = initial_count - len(self.tokens)
#             if removed_count > 0:
#                 logger.info(f"Cleaned up {removed_count} old FCM tokens (older than {max_age_days} days)")

# class FCMManager:
#     """Enhanced Firebase Cloud Messaging manager with better error handling"""
#     def __init__(self, config: ServerConfig):
#         self.config = config
#         self._initialize_firebase()
    
#     def _initialize_firebase(self):
#         """Initialize Firebase Admin SDK"""
#         try:
#             # Check if Firebase is already initialized
#             if not firebase_admin._apps:
#                 # Use service account key from environment or file
#                 service_account_path = getattr(self.config, 'FCM_SERVICE_ACCOUNT_PATH', None)
#                 if service_account_path and os.path.exists(service_account_path):
#                     cred = credentials.Certificate(service_account_path)
#                     firebase_admin.initialize_app(cred)
#                     logger.info("Firebase initialized with service account file")
#                 else:
#                     # Use hardcoded service account (for development)
#                     service_account_info = {
#                         "type": "service_account",
#                         "project_id": "ai-iot-notifier",
#                         "private_key_id": "a2357a7c10419857849a02618429db4c821f412d",
#                         "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCp+Syr2xCGPrwo\nT3Sc/4R5rza7nrA1qF0x8O4oHj5m6kK4ZxpcUOzDHAglpIjOXIk4lOpX0TiststW\n4cA+jWpNR9L+zKhpZi0bP5Su2k1njXOO4o9XAlX286VIp425P7AaUuMfwMShwoKX\no11kS6d2tocDPP9VhEEuIU8dgs7EHOYVm9YJPMqsELg8AynPhTDPqJ1IW4+WV/8P\ntOi4xGP09NS64Q8n6S0joslMKMpOFVF1CtZeBhgSOLO+cKQvNfBI6RPWDkzTA83f\nnjWdjr1FcZHe/n0klR4KxTHh5bBWTFczPKeXQz5vH+NMzzCyMONn0fRlYNlDaaZJ\nwAyt4OOpAgMBAAECggEAD3cfjGd7Qmu03QoVty88k4HQvhN7PvaZvDCKytWtodmQ\nxoyDBoFKeZo0V5B37ibXSXGrPOBJgtWC/N2/izF8yZlOZmaisCxe0ErhsWMlhdWF\n/Ss6FZWd0sFqeYjdSUy1Lj/6cGouufUjwr5XggesLg3/jNjg9pv4/kSDmVDMlWVR\nxP68mNMNcYr0mJc+jJLCdWr1Tir5GpvQeqxskPNRobcZkdtJu35fxRhd44E8omLh\nm6p5VNjEjkyMBtvZt5nF1eItUWTb2n4dBzAFyd+SgEX+/hQQxricFRhXf4RwaiyW\ncg2cmIP9fbJNCB9A+uaJ9l7AMChNKgOS2rVQUDTcgQKBgQDWGhqiYER1r7+bG4fa\nLMCtyPviSe3XnMTrqvFmAmRvNY+yVbTZE5qrOGDkbrY8oVB/sJqu+eFVyCiS4doI\nmW3zdBpd+1HOW1p3MRJu7fdczjOLAZZah1+yIo+ppGV62bP9ghCG0GuAMBkeXaUf\n+ZaQsekUZ2+Zw8vChWjLxz4JmQKBgQDLPFox1TRWrWRMU/aapRKaSYtBfhg7BP9u\nTSfUvP2/NfCxL9ulieQnsy7gRuGyZbz2lDj8tB7cLJCQrjpHznj5oE1Ddez+8jBr\n4IQXqLTww8+CjAycl2V4Xq58yJntgeAl46hCAAuPotnU7fMx0IlJAxHZuljp4TYL\nVm3goFmUkQKBgHBFE/5duMh1tmXhk+WGXitDH0JUPhI4NNLXuuohCwV98rIzWzgR\nnaN3VueyXoGAnbO3qgVjJxRSd2Q+ZpTnz84/7aumpAkvwkqKQv5EbtgNkN2toWgr\nYLUKhocQm95F1qpyz7PCCv0XO7S+ql4QBTIu+OgoLU9WarzANGnXOuLRAoGAU4JU\nCV/y5p7OtLJXhUnI8A7CIsIeULoH/xnDAR47IcOXSCdDGK0lS87LtypI+RXm5GcZ\nV3TnrU6+hESi+/hyKxhcRxkAre10Sg9yF4qh9sBu1tSXJgzri99T0UBYR4hzQv5d\nl+kO1xFycpTnthNbJd4WCqIQgOGiZFw6P++Df5ECgYEAlyTUaIt+J35cmfk/kt+z\ne8EV3suVRCdCbLNYsQXGM3yeJlFaGD2Piww3cP7ZPSRP92cM99elGmmuQlKCQ9qD\nBbYx8y2bFipteC8H91QyJlSWBJnUDNTCc52sdVpOTNwcX5s8W822UleZaDMad/Fk\nHE9O7hMyt+mvwzeCWKazLt8=\n-----END PRIVATE KEY-----\n",
#                         "client_email": "firebase-adminsdk-fbsvc@ai-iot-notifier.iam.gserviceaccount.com",
#                         "client_id": "115989306183221339048",
#                         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                         "token_uri": "https://oauth2.googleapis.com/token",
#                         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#                         "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40ai-iot-notifier.iam.gserviceaccount.com",
#                         "universe_domain": "googleapis.com"
#                     }
#                     cred = credentials.Certificate(service_account_info)
#                     firebase_admin.initialize_app(cred)
#                     logger.info("Firebase initialized with service account credentials")
#         except Exception as e:
#             logger.error(f"Failed to initialize Firebase: {e}")
#             logger.warning("FCM functionality will be disabled")

#     def _is_token_error(self, error: Exception) -> bool:
#         """Check if the error is related to invalid token"""
#         error_str = str(error).lower()
#         token_error_indicators = [
#             "requested entity was not found",
#             "registration token is not a valid fcm registration token",
#             "the registration token is not valid",
#             "registration token expired",
#             "invalid token",
#             "invalid registration token"
#         ]
#         return any(indicator in error_str for indicator in token_error_indicators)

#     async def send_notification(self, tokens: List[str], title: str, body: str, data: Dict[str, str] = None, token_manager: 'FCMTokenManager' = None):
#         """Send FCM notification to multiple tokens with enhanced error handling"""
#         if not firebase_admin._apps:
#             logger.warning("Firebase not initialized, skipping FCM notification")
#             return {"successes": 0, "failures": len(tokens), "details": []}
        
#         successes = 0
#         failures = 0
#         details = []
        
#         for token in tokens:
#             try:
#                 message = messaging.Message(
#                     notification=messaging.Notification(
#                         title=title,
#                         body=body
#                     ),
#                     data=data or {},
#                     token=token
#                 )
#                 response = messaging.send(message)
#                 successes += 1
#                 details.append({
#                     "token": token[:20] + "...",
#                     "status": "success",
#                     "response": response
#                 })
#                 logger.debug(f"FCM notification sent successfully to {token[:20]}...")
                
#             except FirebaseError as e:
#                 failures += 1
#                 error_msg = str(e)
#                 details.append({
#                     "token": token[:20] + "...",
#                     "status": "failed",
#                     "error": error_msg
#                 })
                
#                 # Handle token-specific errors
#                 if self._is_token_error(e):
#                     logger.warning(f"Invalid FCM token detected: {token[:20]}... - {error_msg}")
#                     if token_manager:
#                         await token_manager.mark_token_invalid(token, error_msg)
#                 else:
#                     logger.error(f"FCM service error for token {token[:20]}...: {error_msg}")
                
#             except Exception as e:
#                 failures += 1
#                 error_msg = str(e)
#                 details.append({
#                     "token": token[:20] + "...",
#                     "status": "failed",
#                     "error": error_msg
#                 })
#                 logger.error(f"Unexpected error sending FCM notification to {token[:20]}...: {error_msg}")
        
#         return {
#             "successes": successes, 
#             "failures": failures,
#             "details": details
#         }
    

#     import asyncio
# import logging
# from typing import List, Dict, Any, Tuple
# from datetime import datetime, timedelta
# import firebase_admin
# from firebase_admin import messaging
# from firebase_admin.exceptions import FirebaseError

# logger = logging.getLogger(__name__)

# class FCMTokenValidator:
#     """Validates FCM tokens before sending notifications"""
    
#     def __init__(self):
#         self.validation_cache = {}  # Cache validation results
#         self.cache_ttl = 300  # Cache for 5 minutes
    
#     async def validate_token(self, token: str) -> Tuple[bool, str]:
#         """
#         Validate a single FCM token by sending a dry-run message
#         Returns: (is_valid, error_message)
#         """
#         # Check cache first
#         cache_key = token
#         if cache_key in self.validation_cache:
#             cached_result, timestamp = self.validation_cache[cache_key]
#             if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
#                 return cached_result
        
#         try:
#             if not firebase_admin._apps:
#                 return False, "Firebase not initialized"
            
#             # Create a dry-run message to validate the token
#             message = messaging.Message(
#                 notification=messaging.Notification(
#                     title="Token Validation",
#                     body="This is a validation test"
#                 ),
#                 token=token
#             )
            
#             # Send as dry-run (won't actually send notification)
#             messaging.send(message, dry_run=True)
            
#             # Cache successful validation
#             self.validation_cache[cache_key] = ((True, "Valid"), datetime.now())
#             return True, "Valid"
            
#         except FirebaseError as e:
#             error_msg = str(e)
#             # Cache failed validation
#             self.validation_cache[cache_key] = ((False, error_msg), datetime.now())
#             return False, error_msg
#         except Exception as e:
#             error_msg = f"Validation error: {str(e)}"
#             return False, error_msg
    
#     async def validate_tokens_batch(self, tokens: List[str], max_concurrent: int = 5) -> Dict[str, Tuple[bool, str]]:
#         """
#         Validate multiple tokens concurrently
#         Returns: {token: (is_valid, error_message)}
#         """
#         semaphore = asyncio.Semaphore(max_concurrent)
        
#         async def validate_with_semaphore(token):
#             async with semaphore:
#                 return token, await self.validate_token(token)
        
#         tasks = [validate_with_semaphore(token) for token in tokens]
#         results = await asyncio.gather(*tasks)
        
#         return dict(results)
    
#     def clear_cache(self):
#         """Clear validation cache"""
#         self.validation_cache.clear()


# class EnhancedFCMTokenManager:
#     """Enhanced FCM token manager with validation and better error handling"""
    
#     def __init__(self):
#         self.tokens: List[Dict[str, Any]] = []
#         self._lock = asyncio.Lock()
#         self.validator = FCMTokenValidator()
#         self.last_validation = None
#         self.validation_interval = 3600  # Validate tokens every hour
    
#     async def add_token(self, token: str, user_info: Dict[str, Any] = None):
#         """Add a token with metadata and optional validation"""
#         async with self._lock:
#             # Check if token already exists
#             existing_token = next((t for t in self.tokens if t["token"] == token), None)
#             if existing_token:
#                 # Update existing token info
#                 existing_token.update({
#                     "last_seen": datetime.now().isoformat(),
#                     "user_info": user_info or {},
#                     "failed_attempts": 0,  # Reset failed attempts on re-registration
#                     "status": "active"
#                 })
#                 logger.info(f"FCM token updated: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
#                 return False
            
#             # Add new token
#             token_info = {
#                 "token": token,
#                 "added_at": datetime.now().isoformat(),
#                 "last_seen": datetime.now().isoformat(),
#                 "user_info": user_info or {},
#                 "failed_attempts": 0,
#                 "status": "active",  # active, invalid, expired
#                 "last_validation": None,
#                 "validation_error": None
#             }
#             self.tokens.append(token_info)
#             logger.info(f"FCM token registered: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
            
#             # Validate the token in background (don't block registration)
#             asyncio.create_task(self._validate_token_background(token))
            
#             return True
    
#     async def _validate_token_background(self, token: str):
#         """Validate a token in the background"""
#         try:
#             is_valid, error_msg = await self.validator.validate_token(token)
            
#             async with self._lock:
#                 token_info = next((t for t in self.tokens if t["token"] == token), None)
#                 if token_info:
#                     token_info["last_validation"] = datetime.now().isoformat()
#                     if not is_valid:
#                         token_info["status"] = "invalid"
#                         token_info["validation_error"] = error_msg
#                         logger.warning(f"Token validation failed: {token[:20]}... - {error_msg}")
#                     else:
#                         token_info["status"] = "active"
#                         token_info["validation_error"] = None
#                         logger.debug(f"Token validation successful: {token[:20]}...")
#         except Exception as e:
#             logger.error(f"Background token validation error: {e}")
    
#     async def remove_token(self, token: str):
#         """Remove a specific token"""
#         async with self._lock:
#             initial_count = len(self.tokens)
#             self.tokens = [t for t in self.tokens if t["token"] != token]
#             removed = len(self.tokens) < initial_count
#             if removed:
#                 logger.info(f"FCM token removed: {token[:20]}...")
#             return removed
    
#     async def mark_token_invalid(self, token: str, error_message: str = ""):
#         """Mark a token as invalid and increment failure count"""
#         async with self._lock:
#             for token_info in self.tokens:
#                 if token_info["token"] == token:
#                     token_info["failed_attempts"] = token_info.get("failed_attempts", 0) + 1
#                     token_info["last_error"] = error_message
#                     token_info["last_error_at"] = datetime.now().isoformat()
#                     token_info["status"] = "invalid"
                    
#                     # Remove token if it has failed too many times
#                     if token_info["failed_attempts"] >= 3:
#                         logger.warning(f"Removing FCM token after {token_info['failed_attempts']} failures: {token[:20]}...")
#                         await self.remove_token(token)
#                         return True
#                     break
            
#             logger.warning(f"FCM token marked as invalid: {token[:20]}... - {error_message}")
#             return False
    
#     async def get_valid_tokens(self) -> List[str]:
#         """Get list of tokens that are likely to be valid"""
#         async with self._lock:
#             valid_tokens = []
#             for token_info in self.tokens:
#                 # Consider token valid if:
#                 # 1. Status is active
#                 # 2. Failed attempts < 3
#                 # 3. Not marked as invalid
#                 if (token_info.get("status", "active") == "active" and 
#                     token_info.get("failed_attempts", 0) < 3):
#                     valid_tokens.append(token_info["token"])
#             return valid_tokens
    
#     async def get_tokens(self) -> List[str]:
#         """Get all tokens (for backward compatibility)"""
#         return await self.get_valid_tokens()
    
#     async def get_token_info(self) -> List[Dict[str, Any]]:
#         """Get detailed token information"""
#         async with self._lock:
#             return [
#                 {
#                     "token": t["token"][:20] + "...",
#                     "added_at": t["added_at"],
#                     "last_seen": t["last_seen"],
#                     "user_info": t["user_info"],
#                     "failed_attempts": t.get("failed_attempts", 0),
#                     "status": t.get("status", "unknown"),
#                     "last_validation": t.get("last_validation"),
#                     "validation_error": t.get("validation_error"),
#                     "is_valid": t.get("status", "active") == "active" and t.get("failed_attempts", 0) < 3
#                 }
#                 for t in self.tokens
#             ]
    
#     async def validate_all_tokens(self, force: bool = False):
#         """Validate all tokens (run periodically or on demand)"""
#         now = datetime.now()
        
#         # Check if we need to validate (unless forced)
#         if not force and self.last_validation:
#             time_since_last = (now - self.last_validation).total_seconds()
#             if time_since_last < self.validation_interval:
#                 logger.debug(f"Skipping validation, last run {time_since_last:.0f}s ago")
#                 return
        
#         async with self._lock:
#             tokens_to_validate = [t["token"] for t in self.tokens if t.get("status") != "invalid"]
        
#         if not tokens_to_validate:
#             logger.info("No tokens to validate")
#             return
        
#         logger.info(f"Validating {len(tokens_to_validate)} FCM tokens...")
        
#         try:
#             # Validate tokens in batches
#             validation_results = await self.validator.validate_tokens_batch(tokens_to_validate)
            
#             # Update token statuses based on validation results
#             async with self._lock:
#                 for token_info in self.tokens:
#                     token = token_info["token"]
#                     if token in validation_results:
#                         is_valid, error_msg = validation_results[token]
#                         token_info["last_validation"] = now.isoformat()
                        
#                         if is_valid:
#                             token_info["status"] = "active"
#                             token_info["validation_error"] = None
#                             # Reset failed attempts on successful validation
#                             token_info["failed_attempts"] = 0
#                         else:
#                             token_info["status"] = "invalid"
#                             token_info["validation_error"] = error_msg
#                             token_info["failed_attempts"] = token_info.get("failed_attempts", 0) + 1
            
#             valid_count = sum(1 for is_valid, _ in validation_results.values() if is_valid)
#             invalid_count = len(validation_results) - valid_count
            
#             logger.info(f"Token validation completed: {valid_count} valid, {invalid_count} invalid")
#             self.last_validation = now
            
#         except Exception as e:
#             logger.error(f"Error during token validation: {e}")
    
#     async def cleanup_old_tokens(self, max_age_days: int = 30):
#         """Remove tokens older than specified days"""
#         async with self._lock:
#             cutoff_date = datetime.now() - timedelta(days=max_age_days)
#             initial_count = len(self.tokens)
            
#             self.tokens = [
#                 t for t in self.tokens 
#                 if datetime.fromisoformat(t["added_at"].replace('Z', '+00:00').replace('+00:00', '')) > cutoff_date
#             ]
            
#             removed_count = initial_count - len(self.tokens)
#             if removed_count > 0:
#                 logger.info(f"Cleaned up {removed_count} old FCM tokens (older than {max_age_days} days)")

#     async def get_statistics(self) -> Dict[str, Any]:
#         """Get token statistics"""
#         async with self._lock:
#             total = len(self.tokens)
#             if total == 0:
#                 return {"total": 0, "active": 0, "invalid": 0, "recent": 0}
            
#             active = sum(1 for t in self.tokens if t.get("status", "active") == "active")
#             invalid = sum(1 for t in self.tokens if t.get("status") == "invalid")
            
#             # Tokens added in last 24 hours
#             yesterday = datetime.now() - timedelta(days=1)
#             recent = sum(
#                 1 for t in self.tokens 
#                 if datetime.fromisoformat(t["added_at"].replace('Z', '+00:00').replace('+00:00', '')) > yesterday
#             )
            
#             return {
#                 "total": total,
#                 "active": active,
#                 "invalid": invalid,
#                 "recent": recent,
#                 "validation_rate": f"{(active/total)*100:.1f}%" if total > 0 else "0%"
#             }