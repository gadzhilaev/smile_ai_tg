"""
Модуль для работы с базой данных.
Использует SQLite для хранения истории переписок и токенов устройств.
"""
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "support_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Создает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализирует базу данных и создает необходимые таблицы"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблица для истории сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message_text TEXT,
                    photo_url TEXT,
                    direction TEXT NOT NULL,
                    telegram_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для токенов устройств (FCM)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    fcm_token TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    device_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, fcm_token)
                )
            ''')
            
            # Таблица для связи сообщений в Telegram с пользователями
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_message_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("База данных инициализирована успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
    
    def save_message(self, user_id: str, message_text: Optional[str] = None, 
                    photo_url: Optional[str] = None, direction: str = "user",
                    telegram_message_id: Optional[int] = None):
        """Сохраняет сообщение в базу данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (user_id, message_text, photo_url, direction, telegram_message_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, message_text, photo_url, direction, telegram_message_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Сообщение сохранено для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {e}")
            raise
    
    def get_message_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Получает историю переписки пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message_text, photo_url, direction, created_at
                FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Преобразуем в список словарей
            history = []
            for row in rows:
                history.append({
                    "message": row["message_text"],
                    "photo_url": row["photo_url"],
                    "direction": row["direction"],
                    "created_at": row["created_at"]
                })
            
            # Возвращаем в хронологическом порядке (от старых к новым)
            return list(reversed(history))
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            return []
    
    def save_device_token(self, user_id: str, fcm_token: str, platform: str, device_id: Optional[str] = None):
        """Сохраняет или обновляет токен устройства для push уведомлений"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже такой токен
            cursor.execute('''
                SELECT id FROM device_tokens
                WHERE user_id = ? AND fcm_token = ?
            ''', (user_id, fcm_token))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующий токен
                cursor.execute('''
                    UPDATE device_tokens
                    SET updated_at = CURRENT_TIMESTAMP, platform = ?, device_id = ?
                    WHERE user_id = ? AND fcm_token = ?
                ''', (platform, device_id, user_id, fcm_token))
            else:
                # Создаем новый токен
                cursor.execute('''
                    INSERT INTO device_tokens (user_id, fcm_token, platform, device_id)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, fcm_token, platform, device_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Токен устройства сохранен для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении токена устройства: {e}")
            raise
    
    def get_device_tokens(self, user_id: str) -> List[str]:
        """Получает все токены устройств пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT fcm_token FROM device_tokens
                WHERE user_id = ?
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row["fcm_token"] for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка при получении токенов устройств: {e}")
            return []
    
    def save_message_mapping(self, user_id: str, telegram_message_id: int):
        """Сохраняет связь между user_id и telegram_message_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO message_mapping (user_id, telegram_message_id)
                VALUES (?, ?)
            ''', (user_id, telegram_message_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении связи сообщения: {e}")
            raise
    
    def get_user_by_telegram_message(self, telegram_message_id: int) -> Optional[str]:
        """Получает user_id по telegram_message_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id FROM message_mapping
                WHERE telegram_message_id = ?
            ''', (telegram_message_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row["user_id"]
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении user_id: {e}")
            return None

