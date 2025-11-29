"""
Модуль для работы с базой данных.
Хранит историю переписок и токены для push уведомлений.
"""
import sqlite3
import logging
from typing import Optional, List, Dict
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_path: str = "support_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализирует базу данных и создает таблицы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица для истории сообщений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message_text TEXT,
                photo_url TEXT,
                direction TEXT NOT NULL,  -- 'user' или 'support'
                telegram_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для токенов устройств
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,  -- 'android' или 'ios'
                fcm_token TEXT,
                apns_token TEXT,
                device_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, device_id)
            )
        """)
        
        # Таблица для связи сообщений в группе с пользователями
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                telegram_message_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    def save_message(self, user_id: str, message_text: Optional[str], 
                    photo_url: Optional[str], direction: str, 
                    telegram_message_id: Optional[int] = None) -> int:
        """
        Сохраняет сообщение в базу данных
        
        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            photo_url: URL фотографии
            direction: 'user' или 'support'
            telegram_message_id: ID сообщения в Telegram
            
        Returns:
            ID сохраненного сообщения
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO messages (user_id, message_text, photo_url, direction, telegram_message_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, message_text, photo_url, direction, telegram_message_id))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Сообщение сохранено: user_id={user_id}, direction={direction}")
        return message_id
    
    def get_message_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        Получает историю переписки пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            Список сообщений
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, message_text, photo_url, direction, telegram_message_id, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append({
                "id": row["id"],
                "message_text": row["message_text"],
                "photo_url": row["photo_url"],
                "direction": row["direction"],
                "telegram_message_id": row["telegram_message_id"],
                "created_at": row["created_at"]
            })
        
        return list(reversed(messages))  # Возвращаем в хронологическом порядке
    
    def save_message_mapping(self, user_id: str, telegram_message_id: int):
        """
        Сохраняет связь между user_id и telegram_message_id
        
        Args:
            user_id: ID пользователя
            telegram_message_id: ID сообщения в Telegram группе
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO message_mapping (user_id, telegram_message_id)
                VALUES (?, ?)
            """, (user_id, telegram_message_id))
            conn.commit()
        except sqlite3.IntegrityError:
            # Уже существует, обновляем
            cursor.execute("""
                UPDATE message_mapping
                SET user_id = ?
                WHERE telegram_message_id = ?
            """, (user_id, telegram_message_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_user_by_telegram_message(self, telegram_message_id: int) -> Optional[str]:
        """
        Получает user_id по telegram_message_id
        
        Args:
            telegram_message_id: ID сообщения в Telegram
            
        Returns:
            user_id или None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id
            FROM message_mapping
            WHERE telegram_message_id = ?
        """, (telegram_message_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row["user_id"] if row else None
    
    def save_device_token(self, user_id: str, platform: str, 
                         fcm_token: Optional[str] = None,
                         apns_token: Optional[str] = None,
                         device_id: Optional[str] = None):
        """
        Сохраняет токен устройства для push уведомлений
        
        Args:
            user_id: ID пользователя
            platform: 'android' или 'ios'
            fcm_token: FCM токен для Android
            apns_token: APNs токен для iOS
            device_id: ID устройства
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO device_tokens (user_id, platform, fcm_token, apns_token, device_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, platform, fcm_token, apns_token, device_id))
            conn.commit()
        except sqlite3.IntegrityError:
            # Обновляем существующий токен
            cursor.execute("""
                UPDATE device_tokens
                SET fcm_token = ?, apns_token = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND platform = ? AND device_id = ?
            """, (fcm_token, apns_token, user_id, platform, device_id))
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"Токен устройства сохранен: user_id={user_id}, platform={platform}")
    
    def get_device_tokens(self, user_id: str) -> Dict[str, List[str]]:
        """
        Получает все токены устройства пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с токенами: {'fcm': [...], 'apns': [...]}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT platform, fcm_token, apns_token
            FROM device_tokens
            WHERE user_id = ?
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tokens = {"fcm": [], "apns": []}
        for row in rows:
            if row["fcm_token"]:
                tokens["fcm"].append(row["fcm_token"])
            if row["apns_token"]:
                tokens["apns"].append(row["apns_token"])
        
        return tokens

