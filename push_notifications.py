"""
Модуль для отправки push уведомлений через FCM и APNs.
"""
import requests
import logging
from typing import Optional, Dict
from config import FCM_SERVER_KEY, APNS_KEY_ID, APNS_TEAM_ID, APNS_BUNDLE_ID, APNS_KEY_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PushNotificationService:
    """Класс для отправки push уведомлений"""
    
    def __init__(self):
        self.fcm_server_key = FCM_SERVER_KEY
        self.apns_key_id = APNS_KEY_ID
        self.apns_team_id = APNS_TEAM_ID
        self.apns_bundle_id = APNS_BUNDLE_ID
        self.apns_key_path = APNS_KEY_PATH
    
    def send_fcm_notification(self, token: str, title: str, body: str, 
                             data: Optional[Dict] = None) -> bool:
        """
        Отправляет push уведомление через FCM (Android)
        
        Args:
            token: FCM токен устройства
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные для уведомления
            
        Returns:
            True если успешно, False в случае ошибки
        """
        if not self.fcm_server_key:
            logger.warning("FCM_SERVER_KEY не установлен")
            return False
        
        url = "https://fcm.googleapis.com/fcm/send"
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
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
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success") == 1:
                logger.info(f"FCM уведомление отправлено: {token}")
                return True
            else:
                logger.error(f"Ошибка отправки FCM: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке FCM уведомления: {e}")
            return False
    
    def send_apns_notification(self, token: str, title: str, body: str,
                              data: Optional[Dict] = None) -> bool:
        """
        Отправляет push уведомление через APNs (iOS)
        
        Args:
            token: APNs токен устройства
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные для уведомления
            
        Returns:
            True если успешно, False в случае ошибки
        """
        if not all([self.apns_key_id, self.apns_team_id, self.apns_bundle_id, self.apns_key_path]):
            logger.warning("APNs настройки не полностью установлены")
            return False
        
        try:
            import jwt
            import time
            
            # Генерируем JWT токен для APNs
            headers_jwt = {
                "alg": "ES256",
                "kid": self.apns_key_id
            }
            
            payload_jwt = {
                "iss": self.apns_team_id,
                "iat": int(time.time())
            }
            
            # Читаем приватный ключ
            with open(self.apns_key_path, 'r') as f:
                private_key = f.read()
            
            # Создаем JWT
            token_jwt = jwt.encode(payload_jwt, private_key, algorithm="ES256", headers=headers_jwt)
            # PyJWT 2.x возвращает строку, не bytes
            if isinstance(token_jwt, bytes):
                token_jwt = token_jwt.decode('utf-8')
            
            # URL для APNs (production или sandbox)
            apns_url = f"https://api.push.apple.com/3/device/{token}"
            
            headers = {
                "authorization": f"bearer {token_jwt}",
                "apns-topic": self.apns_bundle_id,
                "apns-priority": "10",
                "apns-push-type": "alert"
            }
            
            payload = {
                "aps": {
                    "alert": {
                        "title": title,
                        "body": body
                    },
                    "sound": "default",
                    "badge": 1
                }
            }
            
            # Добавляем кастомные данные
            if data:
                for key, value in data.items():
                    payload[key] = value
            
            response = requests.post(apns_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"APNs уведомление отправлено: {token}")
                return True
            else:
                logger.error(f"Ошибка отправки APNs: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            logger.error("Библиотека PyJWT не установлена для APNs")
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке APNs уведомления: {e}")
            return False
    
    def send_notification(self, tokens: Dict[str, list], title: str, body: str,
                         data: Optional[Dict] = None) -> Dict[str, int]:
        """
        Отправляет уведомления на все устройства пользователя
        
        Args:
            tokens: Словарь с токенами {'fcm': [...], 'apns': [...]}
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные
            
        Returns:
            Словарь с результатами: {'fcm_sent': 0, 'apns_sent': 0}
        """
        results = {"fcm_sent": 0, "apns_sent": 0}
        
        # Отправляем FCM уведомления
        for fcm_token in tokens.get("fcm", []):
            if self.send_fcm_notification(fcm_token, title, body, data):
                results["fcm_sent"] += 1
        
        # Отправляем APNs уведомления
        for apns_token in tokens.get("apns", []):
            if self.send_apns_notification(apns_token, title, body, data):
                results["apns_sent"] += 1
        
        return results

