"""
Модуль для отправки push уведомлений через Firebase Cloud Messaging (FCM).
Использует Firebase Admin SDK (современный и надежный подход).
"""
import logging
from typing import List, Dict, Optional
import os
from config import FCM_SERVICE_ACCOUNT_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Firebase Admin SDK
_firebase_initialized = False

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
    
    # Инициализация Firebase Admin SDK
    if not firebase_admin._apps:
        if os.path.exists(FCM_SERVICE_ACCOUNT_PATH):
            try:
                cred = credentials.Certificate(FCM_SERVICE_ACCOUNT_PATH)
                firebase_admin.initialize_app(cred)
                _firebase_initialized = True
                logger.info("✅ Firebase Admin SDK инициализирован успешно")
                logger.info(f"   Используется файл: {FCM_SERVICE_ACCOUNT_PATH}")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Firebase Admin SDK: {e}")
                logger.error(f"   Проверьте правильность файла {FCM_SERVICE_ACCOUNT_PATH}")
                _firebase_initialized = False
        else:
            logger.warning(f"⚠️  Файл Service Account не найден: {FCM_SERVICE_ACCOUNT_PATH}")
            logger.warning("   Push уведомления не будут работать. См. FCM_SERVER_GUIDE.md для настройки")
            _firebase_initialized = False
    else:
        _firebase_initialized = True
        logger.info("✅ Firebase Admin SDK уже инициализирован")
        
except ImportError:
    logger.error("firebase-admin не установлен. Установите: pip install firebase-admin")
except Exception as e:
    logger.error(f"Ошибка инициализации Firebase Admin SDK: {e}")


class PushNotificationService:
    """Класс для отправки push уведомлений через FCM используя Firebase Admin SDK"""
    
    def __init__(self):
        self.initialized = _firebase_initialized
        
        if not self.initialized:
            logger.warning("Firebase Admin SDK не инициализирован. Push уведомления не будут работать.")
            logger.warning("Инструкции по настройке см. в FCM_SERVER_GUIDE.md")
    
    def send_notification(self, tokens: List[str], title: str, body: str, 
                         data: Dict = None) -> Dict:
        """
        Отправляет push уведомление на устройства используя Firebase Admin SDK.
        
        Args:
            tokens: Список FCM токенов устройств
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные для уведомления
            
        Returns:
            Dict с результатами отправки
        """
        if not self.initialized:
            logger.error("Firebase Admin SDK не инициализирован")
            return {"success": False, "error": "Firebase Admin SDK не инициализирован", "sent": 0, "failed": 0, "errors": []}
        
        if not tokens:
            logger.warning("Список токенов пуст")
            return {"success": False, "error": "Нет токенов для отправки", "sent": 0, "failed": 0, "errors": []}
        
        results = {
            "success": True,
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        # Если один токен, используем send, иначе send_multicast
        if len(tokens) == 1:
            # Отправка одному устройству
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data={str(k): str(v) for k, v in (data or {}).items()},  # Все значения должны быть строками
                    token=tokens[0],
                    android=messaging.AndroidConfig(
                        priority="high",
                    ),
                    apns=messaging.APNSConfig(
                        headers={
                            "apns-priority": "10",
                        },
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound="default",
                                badge=1,
                            ),
                        ),
                    ),
                )
                
                response = messaging.send(message)
                results["sent"] = 1
                logger.info(f"Push уведомление отправлено на устройство {tokens[0][:20]}...")
                logger.debug(f"Response: {response}")
                
            except messaging.UnregisteredError:
                results["failed"] = 1
                results["errors"].append(f"Token {tokens[0][:20]}...: недействителен (UnregisteredError)")
                logger.warning(f"Токен {tokens[0][:20]}... недействителен и должен быть удален из БД")
            except FirebaseError as e:
                results["failed"] = 1
                results["errors"].append(f"Token {tokens[0][:20]}...: {str(e)}")
                logger.error(f"Ошибка Firebase при отправке push: {e}")
            except Exception as e:
                results["failed"] = 1
                results["errors"].append(f"Token {tokens[0][:20]}...: {str(e)}")
                logger.error(f"Неожиданная ошибка при отправке push: {e}")
        else:
            # Отправка нескольким устройствам
            try:
                multicast_message = messaging.MulticastMessage(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data={str(k): str(v) for k, v in (data or {}).items()},
                    tokens=tokens,
                    android=messaging.AndroidConfig(
                        priority="high",
                    ),
                    apns=messaging.APNSConfig(
                        headers={
                            "apns-priority": "10",
                        },
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound="default",
                                badge=1,
                            ),
                        ),
                    ),
                )
                
                response = messaging.send_multicast(multicast_message)
                results["sent"] = response.success_count
                results["failed"] = response.failure_count
                
                logger.info(f"Push уведомления отправлены: успешно={response.success_count}, ошибок={response.failure_count}")
                
                # Обрабатываем ошибки
                if response.failure_count > 0:
                    for idx, response_item in enumerate(response.responses):
                        if not response_item.success:
                            error = response_item.exception
                            token = tokens[idx]
                            error_msg = str(error) if error else "Unknown error"
                            results["errors"].append(f"Token {token[:20]}...: {error_msg}")
                            
                            # Если токен недействителен, логируем для удаления
                            if isinstance(error, messaging.UnregisteredError):
                                logger.warning(f"Токен {token[:20]}... недействителен и должен быть удален из БД")
                
            except FirebaseError as e:
                results["failed"] = len(tokens)
                results["errors"].append(f"Firebase error: {str(e)}")
                logger.error(f"Ошибка Firebase при отправке multicast: {e}")
            except Exception as e:
                results["failed"] = len(tokens)
                results["errors"].append(f"Unexpected error: {str(e)}")
                logger.error(f"Неожиданная ошибка при отправке multicast: {e}")
        
        if results["failed"] > 0:
            results["success"] = False
        
        return results
    
    def send_support_reply_notification(self, tokens: List[str], message: str, user_id: str):
        """
        Отправляет уведомление о ответе от поддержки.
        
        Args:
            tokens: Список FCM токенов устройств
            message: Текст ответа от поддержки
            user_id: ID пользователя
        """
        # Обрезаем текст для уведомления (первые 100 символов)
        notification_body = message[:100] + "..." if len(message) > 100 else message
        
        data = {
            "type": "support_reply",
            "user_id": user_id,
            "message": message,
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        }
        
        return self.send_notification(
            tokens=tokens,
            title="Ответ от поддержки",
            body=notification_body,
            data=data
        )


# Простая функция для тестирования (как в гайде)
def send_push(device_token: str, title: str, body: str, data: dict = None):
    """
    Простая функция для отправки push уведомления одному устройству.
    Используется для тестирования.
    
    Args:
        device_token: FCM токен устройства
        title: Заголовок уведомления
        body: Текст уведомления
        data: Дополнительные данные (опционально)
    
    Returns:
        Dict с результатом отправки
    """
    service = PushNotificationService()
    return service.send_notification(
        tokens=[device_token],
        title=title,
        body=body,
        data=data or {}
    )
