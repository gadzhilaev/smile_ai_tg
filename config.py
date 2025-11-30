"""
Конфигурационный файл для настроек бота.
Все настройки можно хранить здесь или в переменных окружения.
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# ID группы, куда будут отправляться сообщения
# Чтобы получить ID группы, добавьте бота в группу и отправьте любое сообщение
# Затем используйте метод getUpdates или посмотрите в логах
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '')

# Порт для сервера
SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))

# Хост для сервера
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')

# Секретный ключ для API (опционально, для безопасности)
API_SECRET_KEY = os.getenv('API_SECRET_KEY', '')

# URL Telegram Bot API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# FCM настройки (для Android и iOS push уведомлений)
FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY', '')

# Директория для загрузки файлов
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

