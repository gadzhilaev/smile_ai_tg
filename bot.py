import requests
import logging
from typing import Optional, Dict, List
from config import TELEGRAM_API_URL, GROUP_CHAT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.api_url = TELEGRAM_API_URL
        self.group_chat_id = GROUP_CHAT_ID
        
    def send_message_to_group(self, user_id: str, user_name: str, message_text: str, 
                              photo_path: Optional[str] = None) -> Optional[Dict]:
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
    
    def send_media_group_to_group(self, user_id: str, user_name: str, message_text: str,
                                  photo_paths: List[str]) -> Optional[Dict]:
        """
        Отправляет несколько фото как медиагруппу в группу поддержки.
        
        Args:
            user_id: ID пользователя из мобильного приложения
            user_name: Имя пользователя (опционально)
            message_text: Текст сообщения
            photo_paths: Список путей к файлам фотографий
            
        Returns:
            Dict с информацией об отправленном сообщении или None в случае ошибки
        """
        if not self.group_chat_id:
            logger.error("GROUP_CHAT_ID не установлен в конфигурации")
            return None
        
        if not photo_paths or len(photo_paths) == 0:
            logger.error("Список фото пуст")
            return None
        
        # Форматируем сообщение для группы (будет в подписи первого фото)
        formatted_message = f"📱 <b>Сообщение от пользователя</b>\n\n"
        formatted_message += f"👤 <b>ID пользователя:</b> {user_id}\n"
        if user_name:
            formatted_message += f"📝 <b>Имя:</b> {user_name}\n"
        formatted_message += f"\n💬 <b>Сообщение:</b>\n{message_text}"
        formatted_message += f"\n\n📷 <b>Фото:</b> {len(photo_paths)} шт."
        
        try:
            # Подготавливаем медиагруппу
            media = []
            files_dict = {}
            
            for idx, photo_path in enumerate(photo_paths):
                photo_file = open(photo_path, 'rb')
                file_key = f'photo_{idx}'
                files_dict[file_key] = photo_file
                
                media_item = {
                    'type': 'photo',
                    'media': f'attach://{file_key}'
                }
                
                # Подпись только к первому фото
                if idx == 0:
                    media_item['caption'] = formatted_message
                    media_item['parse_mode'] = 'HTML'
                
                media.append(media_item)
            
            # Отправляем медиагруппу
            import json
            
            # Конвертируем media в JSON строку
            media_json = json.dumps(media)
            
            data = {
                'chat_id': self.group_chat_id,
                'media': media_json
            }
            
            response = requests.post(
                f"{self.api_url}/sendMediaGroup",
                files=files_dict,
                data=data,
                timeout=60  # Больше времени для нескольких фото
            )
            
            # Закрываем файлы
            for file in files_dict.values():
                file.close()
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                # Возвращаем ID первого сообщения из группы
                messages = result.get("result", [])
                if messages:
                    message_id = messages[0].get("message_id")
                    logger.info(f"Медиагруппа отправлена в группу. Message ID: {message_id}, фото: {len(photo_paths)}")
                    return {
                        "message_id": message_id,
                        "user_id": user_id,
                        "group_message_id": message_id
                    }
                else:
                    logger.error("Пустой результат отправки медиагруппы")
                    return None
            else:
                logger.error(f"Ошибка отправки медиагруппы: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке медиагруппы в группу: {e}")
            return None
        except FileNotFoundError as e:
            logger.error(f"Файл фотографии не найден: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке медиагруппы: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

