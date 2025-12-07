import sqlite3
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "support_bot.db"):
        # Проверяем, существует ли директория data
        if os.path.exists("data") and os.path.isdir("data"):
            # Используем директорию data для базы данных
            self.db_path = os.path.join("data", os.path.basename(db_path))
        else:
            # Используем текущую директорию
            self.db_path = os.path.join(os.getcwd(), os.path.basename(db_path))
        
        # Создаем директорию для базы данных, если нужно
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, mode=0o777, exist_ok=True)
            except Exception as e:
                logger.error(f"Не удалось создать директорию {db_dir}: {e}")
                # Fallback: используем текущую директорию
                self.db_path = os.path.join(os.getcwd(), os.path.basename(db_path))
        
        # Убеждаемся, что директория имеет права на запись
        try:
            db_dir = os.path.dirname(self.db_path)
            if os.path.exists(db_dir):
                os.chmod(db_dir, 0o777)
        except Exception as e:
            logger.warning(f"Не удалось установить права на директорию {db_dir}: {e}")
        
        logger.info(f"Используется база данных: {self.db_path}")
        self.init_database()
    
    def get_connection(self):
        try:
            # Проверяем, что директория существует и доступна для записи
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o777, exist_ok=True)
            
            # Проверяем права на запись в директорию
            if db_dir and os.path.exists(db_dir):
                test_file = os.path.join(db_dir, '.test_write')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                except Exception as e:
                    logger.error(f"Нет прав на запись в директорию {db_dir}: {e}")
                    # Пытаемся установить права
                    try:
                        os.chmod(db_dir, 0o777)
                    except:
                        pass
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            logger.error(f"Ошибка подключения к базе данных {self.db_path}: {e}")
            logger.error(f"Текущая рабочая директория: {os.getcwd()}")
            logger.error(f"Права на директорию: {oct(os.stat(db_dir).st_mode) if db_dir and os.path.exists(db_dir) else 'N/A'}")
            raise
    
    def init_database(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_message_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS greetings_sent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    greeting_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, greeting_date)
                )
            ''')
            
            # Table for tracking user support mode (AI or human)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_support_mode (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    mode TEXT NOT NULL DEFAULT 'ai',
                    last_user_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    switched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            history = []
            for row in rows:
                history.append({
                    "message": row["message_text"],
                    "photo_url": row["photo_url"],
                    "direction": row["direction"],
                    "created_at": row["created_at"]
                })
            
            return list(reversed(history))
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            return []
    
    def save_device_token(self, user_id: str, fcm_token: str, platform: str, device_id: Optional[str] = None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM device_tokens
                WHERE user_id = ? AND fcm_token = ?
            ''', (user_id, fcm_token))
            
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE device_tokens
                    SET updated_at = CURRENT_TIMESTAMP, platform = ?, device_id = ?
                    WHERE user_id = ? AND fcm_token = ?
                ''', (platform, device_id, user_id, fcm_token))
            else:
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
    
    def get_last_message_time(self, user_id: str) -> Optional[str]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT created_at FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row["created_at"]
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении времени последнего сообщения: {e}")
            return None
    
    def has_messages(self, user_id: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as count FROM messages
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return row["count"] > 0 if row else False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке наличия сообщений: {e}")
            return False
    
    def was_greeting_sent_today(self, user_id: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM greetings_sent
                WHERE user_id = ? AND greeting_date = DATE('now')
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return row is not None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке приветствия: {e}")
            return False
    
    def mark_greeting_sent(self, user_id: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO greetings_sent (user_id, greeting_date)
                VALUES (?, DATE('now'))
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении отметки о приветствии: {e}")
            raise
    
    def get_user_support_mode(self, user_id: str) -> str:
        """Get current support mode for user ('ai' or 'human')"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mode FROM user_support_mode
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row["mode"]
            return "ai"  # Default to AI mode
            
        except Exception as e:
            logger.error(f"Ошибка при получении режима поддержки: {e}")
            return "ai"
    
    def set_user_support_mode(self, user_id: str, mode: str):
        """Set support mode for user ('ai' or 'human')"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_support_mode (user_id, mode, switched_at, last_user_message_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET 
                    mode = excluded.mode,
                    switched_at = CURRENT_TIMESTAMP
            ''', (user_id, mode))
            
            conn.commit()
            conn.close()
            logger.info(f"Режим поддержки для пользователя {user_id} установлен на: {mode}")
            
        except Exception as e:
            logger.error(f"Ошибка при установке режима поддержки: {e}")
            raise
    
    def update_last_user_message_time(self, user_id: str):
        """Update the last user message timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_support_mode (user_id, mode, last_user_message_at)
                VALUES (?, 'ai', CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET 
                    last_user_message_at = CURRENT_TIMESTAMP
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени последнего сообщения: {e}")
    
    def get_last_user_message_time(self, user_id: str) -> Optional[datetime]:
        """Get the last user message timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_user_message_at FROM user_support_mode
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row["last_user_message_at"]:
                return datetime.strptime(row["last_user_message_at"], '%Y-%m-%d %H:%M:%S')
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении времени последнего сообщения: {e}")
            return None
    
    def should_reset_to_ai_mode(self, user_id: str, timeout_minutes: int = 5) -> bool:
        """Check if user should be reset to AI mode due to inactivity"""
        try:
            mode = self.get_user_support_mode(user_id)
            if mode != "human":
                return False
            
            last_message_time = self.get_last_user_message_time(user_id)
            if not last_message_time:
                return False
            
            now = datetime.now()
            time_diff = (now - last_message_time).total_seconds() / 60
            
            return time_diff >= timeout_minutes
            
        except Exception as e:
            logger.error(f"Ошибка при проверке сброса режима: {e}")
            return False

