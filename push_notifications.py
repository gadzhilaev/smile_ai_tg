"""
Модуль для отправки push уведомлений через Firebase Cloud Messaging (FCM).
Поддерживает как Android, так и iOS через единый FCM API.
"""
import requests
import logging
from typing import List, Dict
from config import FCM_SERVER_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PushNotificationService:
    """Класс для отправки push уведомлений через FCM"""
    
    def __init__(self):
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        self.server_key = FCM_SERVER_KEY
        
        if not self.server_key:
            logger.warning("FCM_SERVER_KEY не установлен. Push уведомления не будут работать.")
    
    def send_notification(self, tokens: List[str], title: str, body: str, 
                         data: Dict = None) -> Dict:
        """
        Отправляет push уведомление на устройства.
        
        Args:
            tokens: Список FCM токенов устройств
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные для уведомления
            
        Returns:
            Dict с результатами отправки
        """
        if not self.server_key:
            logger.error("FCM_SERVER_KEY не установлен")
            return {"success": False, "error": "FCM_SERVER_KEY не установлен"}
        
        if not tokens:
            logger.warning("Список токенов пуст")
            return {"success": False, "error": "Нет токенов для отправки"}
        
        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json"
        }
        
        results = {
            "success": True,
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        # Отправляем на каждое устройство отдельно
        for token in tokens:
            try:
                payload = {
                    "to": token,
                    "notification": {
                        "title": title,
                        "body": body,
                        "sound": "default"
                    },
                    "data": data or {},
                    "priority": "high"
                }
                
                response = requests.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("success") == 1:
                    results["sent"] += 1
                    logger.info(f"Push уведомление отправлено на устройство {token[:20]}...")
                else:
                    results["failed"] += 1
                    error_msg = result.get("results", [{}])[0].get("error", "Unknown error")
                    results["errors"].append(f"Token {token[:20]}...: {error_msg}")
                    logger.error(f"Ошибка отправки push на {token[:20]}...: {error_msg}")
                    
                    # Если токен недействителен, можно удалить его из базы
                    if error_msg in ["InvalidRegistration", "NotRegistered"]:
                        logger.warning(f"Токен {token[:20]}... недействителен и должен быть удален")
                
            except requests.exceptions.RequestException as e:
                results["failed"] += 1
                results["errors"].append(f"Token {token[:20]}...: {str(e)}")
                logger.error(f"Ошибка при отправке push на {token[:20]}...: {e}")
        
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
        data = {
            "type": "support_reply",
            "user_id": user_id,
            "message": message,
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        }
        
        return self.send_notification(
            tokens=tokens,
            title="Ответ от поддержки",
            body=message,
            data=data
        )

