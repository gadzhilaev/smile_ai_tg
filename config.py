import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '')
SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
API_SECRET_KEY = os.getenv('API_SECRET_KEY', '')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FCM_SERVICE_ACCOUNT_PATH = os.getenv('FCM_SERVICE_ACCOUNT_PATH', 'firebase-service-account.json')
FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY', '')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024

