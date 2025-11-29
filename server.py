"""
Сервер для приема запросов от мобильного приложения.
Использует Flask для обработки HTTP запросов.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import threading
import time
import os
import uuid
from werkzeug.utils import secure_filename
from bot import TelegramBot
from database import Database
from push_notifications import PushNotificationService
from config import (SERVER_PORT, SERVER_HOST, API_SECRET_KEY, 
                   UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для мобильного приложения

# Инициализация компонентов
bot = TelegramBot()
db = Database()
push_service = PushNotificationService()

# Создаем директорию для загрузки файлов
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Проверяет, разрешен ли тип файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_telegram_updates():
    """
    Фоновая функция для обработки обновлений от Telegram.
    Проверяет reply в группе и отправляет push уведомления пользователям.
    """
    last_update_id = None
    
    while True:
        try:
            updates = bot.get_updates(last_update_id)
            
            if updates:
                for update in updates:
                    update_id = update.get("update_id")
                    last_update_id = update_id
                    
                    # Проверяем, есть ли сообщение
                    message = update.get("message")
                    if not message:
                        continue
                    
                    # Проверяем, является ли это reply в группе
                    reply_to_message = message.get("reply_to_message")
                    if reply_to_message:
                        # Получаем ID сообщения, на которое ответили
                        replied_message_id = reply_to_message.get("message_id")
                        
                        # Ищем пользователя по message_id в базе данных
                        user_id = db.get_user_by_telegram_message(replied_message_id)
                        
                        if user_id:
                            # Получаем текст ответа
                            reply_text = message.get("text", "")
                            if reply_text:
                                # Сохраняем ответ в базу данных
                                db.save_message(
                                    user_id=user_id,
                                    message_text=reply_text,
                                    photo_url=None,
                                    direction="support",
                                    telegram_message_id=message.get("message_id")
                                )
                                
                                # Получаем токены устройства пользователя
                                tokens = db.get_device_tokens(user_id)
                                
                                # Отправляем push уведомления
                                push_data = {
                                    "type": "support_reply",
                                    "user_id": user_id,
                                    "message": reply_text
                                }
                                
                                results = push_service.send_notification(
                                    tokens=tokens,
                                    title="Ответ от поддержки",
                                    body=reply_text,
                                    data=push_data
                                )
                                
                                logger.info(f"Ответ отправлен пользователю {user_id}: {reply_text}")
                                logger.info(f"Push уведомления: FCM={results['fcm_sent']}, APNs={results['apns_sent']}")
                        else:
                            logger.warning(f"Не найден user_id для message_id {replied_message_id}")
            
            time.sleep(1)  # Небольшая задержка между проверками
            
        except Exception as e:
            logger.error(f"Ошибка в процессе обработки обновлений: {e}")
            time.sleep(5)


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({"status": "ok"}), 200


@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Эндпоинт для приема сообщений от мобильного приложения.
    
    Поддерживает multipart/form-data для загрузки фото:
    - user_id (обязательно)
    - message (обязательно)
    - user_name (опционально)
    - photo (опционально, файл изображения)
    
    Или JSON формат:
    {
        "user_id": "123456789",
        "user_name": "Имя пользователя" (опционально),
        "message": "Текст сообщения",
        "photo_url": "https://..." (опционально, если фото уже загружено)
    }
    """
    try:
        photo_path = None
        photo_url = None
        
        # Проверяем, есть ли файл в запросе
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                # Генерируем уникальное имя файла
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                # Проверяем размер файла
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    return jsonify({"error": f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024}MB"}), 400
                
                file.save(photo_path)
                photo_url = f"/uploads/{unique_filename}"
                logger.info(f"Фото сохранено: {photo_path}")
        
        # Получаем данные из формы или JSON
        if request.is_json:
            data = request.get_json()
            user_id = data.get("user_id")
            message_text = data.get("message")
            user_name = data.get("user_name", "")
            photo_url = data.get("photo_url")  # Если фото уже загружено где-то еще
        else:
            user_id = request.form.get("user_id")
            message_text = request.form.get("message")
            user_name = request.form.get("user_name", "")
        
        if not user_id or not message_text:
            # Удаляем загруженный файл если есть ошибка
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            return jsonify({"error": "Отсутствуют обязательные поля: user_id или message"}), 400
        
        # Отправляем сообщение в группу Telegram
        result = bot.send_message_to_group(
            user_id=user_id,
            user_name=user_name,
            message_text=message_text,
            photo_path=photo_path
        )
        
        if result:
            # Сохраняем сообщение в базу данных
            telegram_message_id = result.get("group_message_id")
            db.save_message(
                user_id=user_id,
                message_text=message_text,
                photo_url=photo_url,
                direction="user",
                telegram_message_id=telegram_message_id
            )
            
            # Сохраняем связь между message_id в группе и user_id
            db.save_message_mapping(user_id, telegram_message_id)
            
            return jsonify({
                "success": True,
                "message_id": result.get("message_id"),
                "photo_url": photo_url
            }), 200
        else:
            # Удаляем загруженный файл если не удалось отправить
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            return jsonify({"error": "Не удалось отправить сообщение в группу"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        # Удаляем загруженный файл в случае ошибки
        if 'photo_path' in locals() and photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
        return jsonify({"error": str(e)}), 500


@app.route('/register_device', methods=['POST'])
def register_device():
    """
    Регистрирует токен устройства для push уведомлений.
    
    JSON формат:
    {
        "user_id": "123456789",
        "platform": "android" или "ios",
        "fcm_token": "..." (для Android),
        "apns_token": "..." (для iOS),
        "device_id": "..." (опционально)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Отсутствуют данные"}), 400
        
        user_id = data.get("user_id")
        platform = data.get("platform")
        
        if not user_id or not platform:
            return jsonify({"error": "Отсутствуют обязательные поля: user_id или platform"}), 400
        
        if platform not in ["android", "ios"]:
            return jsonify({"error": "platform должен быть 'android' или 'ios'"}), 400
        
        fcm_token = data.get("fcm_token") if platform == "android" else None
        apns_token = data.get("apns_token") if platform == "ios" else None
        device_id = data.get("device_id", "")
        
        if platform == "android" and not fcm_token:
            return jsonify({"error": "fcm_token обязателен для Android"}), 400
        
        if platform == "ios" and not apns_token:
            return jsonify({"error": "apns_token обязателен для iOS"}), 400
        
        # Сохраняем токен
        db.save_device_token(
            user_id=user_id,
            platform=platform,
            fcm_token=fcm_token,
            apns_token=apns_token,
            device_id=device_id
        )
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации устройства: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/message_history/<user_id>', methods=['GET'])
def get_message_history(user_id):
    """
    Получает историю переписки пользователя.
    
    Query параметры:
    - limit: количество сообщений (по умолчанию 50)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = db.get_message_history(user_id, limit)
        
        return jsonify({
            "success": True,
            "messages": history
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    """Отдает загруженные файлы"""
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    # Запускаем фоновый поток для обработки обновлений Telegram
    update_thread = threading.Thread(target=process_telegram_updates, daemon=True)
    update_thread.start()
    
    logger.info(f"Сервер запущен на {SERVER_HOST}:{SERVER_PORT}")
    logger.info("Бот и сервер работают одновременно")
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
