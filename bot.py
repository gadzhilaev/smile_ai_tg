"""
Модуль для работы с Telegram Bot API.
Обрабатывает отправку сообщений в группу и получение ответов.
"""
import requests
import logging
from typing import Optional, Dict
from config import TELEGRAM_API_URL, GROUP_CHAT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Класс для работы с Telegram ботом"""
    
    def __init__(self):
        self.api_url = TELEGRAM_API_URL
        self.group_chat_id = GROUP_CHAT_ID
        
    def send_message_to_group(self, user_id: str, user_name: str, message_text: str, 
                             photo_path: Optional[str] = None) -> Optional[Dict]:
        """
        Отправляет сообщение от пользователя в группу поддержки.
        
        Args:
            user_id: ID пользователя из мобильного приложения
            user_name: Имя пользователя (опционально)
            message_text: Текст сообщения
            photo_path: Путь к файлу фотографии (опционально)
            
        Returns:
            Dict с информацией об отправленном сообщении или None в случае ошибки
        """
        if not self.group_chat_id:
            logger.error("GROUP_CHAT_ID не установлен в конфигурации")
            return None
            
        # Форматируем сообщение для группы
        formatted_message = f"📱 <b>Сообщение от пользователя</b>\n\n"
        formatted_message += f"👤 <b>ID пользователя:</b> {user_id}\n"
        if user_name:
            formatted_message += f"📝 <b>Имя:</b> {user_name}\n"
        formatted_message += f"\n💬 <b>Сообщение:</b>\n{message_text}"
        
        try:
            if photo_path:
                # Отправляем фото с подписью
                with open(photo_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': self.group_chat_id,
                        'caption': formatted_message,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(
                        f"{self.api_url}/sendPhoto",
                        files=files,
                        data=data,
                        timeout=30
                    )
            else:
                # Отправляем только текст
                response = requests.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.group_chat_id,
                        "text": formatted_message,
                        "parse_mode": "HTML"
                    },
                    timeout=10
                )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                message_id = result["result"]["message_id"]
                logger.info(f"Сообщение отправлено в группу. Message ID: {message_id}")
                return {
                    "message_id": message_id,
                    "user_id": user_id,
                    "group_message_id": message_id
                }
            else:
                logger.error(f"Ошибка отправки сообщения: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке сообщения в группу: {e}")
            return None
        except FileNotFoundError:
            logger.error(f"Файл фотографии не найден: {photo_path}")
            return None
    
    def send_reply_to_user(self, user_id: str, reply_text: str) -> bool:
        """
        Отправляет ответ пользователю.
        
        Args:
            user_id: ID пользователя, которому нужно отправить ответ
            reply_text: Текст ответа
            
        Returns:
            True если сообщение отправлено успешно, False в случае ошибки
        """
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": reply_text
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Ответ отправлен пользователю {user_id}")
                return True
            else:
                logger.error(f"Ошибка отправки ответа: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке ответа пользователю: {e}")
            return False
    
    def get_updates(self, offset: Optional[int] = None) -> Optional[Dict]:
        """
        Получает обновления от Telegram (для обработки reply в группе).
        
        Args:
            offset: ID последнего обработанного обновления
            
        Returns:
            Dict с обновлениями или None в случае ошибки
        """
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset + 1
                
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params=params,
                timeout=35
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return result.get("result", [])
            else:
                logger.error(f"Ошибка получения обновлений: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении обновлений: {e}")
            return None

