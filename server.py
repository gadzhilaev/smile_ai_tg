from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
import logging
import threading
import time
import os
import uuid
import json
from werkzeug.utils import secure_filename
from bot import TelegramBot
from database import Database
from push_notifications import PushNotificationService
from config import (SERVER_PORT, SERVER_HOST, API_SECRET_KEY, 
                   UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

bot = TelegramBot()
db = Database()
push_service = PushNotificationService()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
active_connections = {}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_telegram_updates():
    last_update_id = None
    
    while True:
        try:
            updates = bot.get_updates(last_update_id)
            
            if updates:
                for update in updates:
                    update_id = update.get("update_id")
                    last_update_id = update_id
                    
                    message = update.get("message")
                    if not message:
                        continue
                    
                    reply_to_message = message.get("reply_to_message")
                    if reply_to_message:
                        replied_message_id = reply_to_message.get("message_id")
                        user_id = db.get_user_by_telegram_message(replied_message_id)
                        
                        if user_id:
                            reply_text = message.get("text", "")
                            if reply_text:
                                db.save_message(
                                    user_id=user_id,
                                    message_text=reply_text,
                                    photo_url=None,
                                    direction="support",
                                    telegram_message_id=message.get("message_id")
                                )
                                
                                tokens = db.get_device_tokens(user_id)
                                
                                if not tokens:
                                    logger.warning(f"Для пользователя {user_id} нет зарегистрированных устройств")
                                else:
                                    logger.info(f"Найдено {len(tokens)} устройств для пользователя {user_id}")
                                
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
                                
                                if user_id in active_connections:
                                    socketio.emit('new_message', {
                                        'user_id': user_id,
                                        'message': reply_text,
                                        'direction': 'support',
                                        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
                                    }, room=user_id)
                                
                                if results and isinstance(results, dict):
                                    sent = results.get('sent', 0)
                                    failed = results.get('failed', 0)
                                    logger.info(f"Push уведомления: отправлено={sent}, ошибок={failed}")
                                    if failed > 0:
                                        errors = results.get('errors', [])
                                        for error in errors[:3]:
                                            logger.error(f"  - {error}")
                                else:
                                    logger.warning(f"Неожиданный формат результатов push: {results}")
                        else:
                            logger.warning(f"Не найден user_id для message_id {replied_message_id}")
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка в процессе обработки обновлений: {e}")
            time.sleep(5)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        photo_paths = []
        photo_urls = []
        
        if 'photo' in request.files:
            files = request.files.getlist('photo')
            
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        for saved_path in photo_paths:
                            if os.path.exists(saved_path):
                                os.remove(saved_path)
                        return jsonify({"error": f"Файл {file.filename} слишком большой. Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024}MB"}), 400
                    
                    file.save(photo_path)
                    photo_paths.append(photo_path)
                    photo_urls.append(f"/uploads/{unique_filename}")
        
        photo_path = photo_paths[0] if photo_paths else None
        photo_url = photo_urls[0] if photo_urls else None
        
        if request.is_json:
            data = request.get_json()
            user_id = data.get("user_id")
            message_text = data.get("message")
            user_name = data.get("user_name", "")
            photo_url = data.get("photo_url")
        else:
            user_id = request.form.get("user_id")
            message_text = request.form.get("message")
            user_name = request.form.get("user_name", "")
        
        if not user_id or not message_text:
            for path in photo_paths:
                if os.path.exists(path):
                    os.remove(path)
            return jsonify({"error": "Отсутствуют обязательные поля: user_id или message"}), 400
        
        if len(photo_paths) > 1:
            result = bot.send_media_group_to_group(
                user_id=user_id,
                user_name=user_name,
                message_text=message_text,
                photo_paths=photo_paths
            )
        else:
            result = bot.send_message_to_group(
                user_id=user_id,
                user_name=user_name,
                message_text=message_text,
                photo_path=photo_path
            )
        
        if result:
            telegram_message_id = result.get("group_message_id")
            photo_url_for_db = photo_url if len(photo_urls) <= 1 else json.dumps(photo_urls)
            
            db.save_message(
                user_id=user_id,
                message_text=message_text,
                photo_url=photo_url_for_db,
                direction="user",
                telegram_message_id=telegram_message_id
            )
            
            db.save_message_mapping(user_id, telegram_message_id)
            
            if user_id in active_connections:
                socketio.emit('new_message', {
                    'user_id': user_id,
                    'message': message_text,
                    'photo_url': photo_url if len(photo_urls) <= 1 else photo_urls,
                    'direction': 'user',
                    'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }, room=user_id)
            
            return jsonify({
                "success": True,
                "message_id": result.get("message_id"),
                "photo_url": photo_url if len(photo_urls) <= 1 else photo_urls,
                "photo_count": len(photo_urls)
            }), 200
        else:
            for path in photo_paths:
                if os.path.exists(path):
                    os.remove(path)
            return jsonify({"error": "Не удалось отправить сообщение в группу"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if 'photo_paths' in locals():
            for path in photo_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
        return jsonify({"error": str(e)}), 500


@app.route('/register_device', methods=['POST'])
def register_device():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Отсутствуют данные"}), 400
        
        user_id = data.get("user_id")
        fcm_token = data.get("fcm_token")
        platform = data.get("platform", "android")
        device_id = data.get("device_id", "")
        
        if not user_id or not fcm_token:
            return jsonify({"error": "Отсутствуют обязательные поля: user_id или fcm_token"}), 400
        
        if platform not in ["android", "ios"]:
            return jsonify({"error": "platform должен быть 'android' или 'ios'"}), 400
        
        try:
            db.save_device_token(
                user_id=user_id,
                fcm_token=fcm_token,
                platform=platform,
                device_id=device_id
            )
            
            tokens = db.get_device_tokens(user_id)
            
            return jsonify({
                "success": True,
                "message": "Устройство зарегистрировано успешно",
                "device_count": len(tokens)
            }), 200
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении токена устройства: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": f"Ошибка при сохранении токена: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации устройства: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/message_history/<user_id>', methods=['GET'])
def get_message_history(user_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        user_name = request.args.get('user_name', '')
        
        should_send_greeting = False
        
        if not db.was_greeting_sent_today(user_id):
            should_send_greeting = True
            greeting_text = f"Здравствуйте, {user_name}!" if user_name else "Здравствуйте!"
            
            db.save_message(
                user_id=user_id,
                message_text=greeting_text,
                photo_url=None,
                direction="support",
                telegram_message_id=None
            )
            
            db.mark_greeting_sent(user_id)
            logger.info(f"Приветственное сообщение отправлено для пользователя {user_id}")
            
            if user_id in active_connections:
                socketio.emit('new_message', {
                    'user_id': user_id,
                    'message': greeting_text,
                    'direction': 'support',
                    'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }, room=user_id)
        
        history = db.get_message_history(user_id, limit)
        
        return jsonify({
            "success": True,
            "messages": history,
            "greeting_sent": should_send_greeting
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/check_device/<user_id>', methods=['GET'])
def check_device(user_id):
    try:
        tokens = db.get_device_tokens(user_id)
        return jsonify({
            "user_id": user_id,
            "registered": len(tokens) > 0,
            "device_count": len(tokens),
            "has_tokens": len(tokens) > 0
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при проверке устройства: {e}")
        return jsonify({"error": str(e)}), 500


@socketio.on('connect')
def handle_connect():
    logger.info(f"WebSocket подключение: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    for user_id, connections in list(active_connections.items()):
        if request.sid in connections:
            connections.remove(request.sid)
            if not connections:
                del active_connections[user_id]
    logger.info(f"WebSocket отключение: {request.sid}")


@socketio.on('join_chat')
def handle_join_chat(data):
    try:
        user_id = data.get('user_id')
        if not user_id:
            emit('error', {'message': 'user_id обязателен'})
            return
        
        socketio.server.enter_room(request.sid, user_id)
        
        if user_id not in active_connections:
            active_connections[user_id] = []
        if request.sid not in active_connections[user_id]:
            active_connections[user_id].append(request.sid)
        
        logger.info(f"Пользователь {user_id} подключился к чату")
        emit('joined', {'user_id': user_id, 'status': 'connected'})
        
    except Exception as e:
        logger.error(f"Ошибка при подключении к чату: {e}")
        emit('error', {'message': str(e)})


@socketio.on('leave_chat')
def handle_leave_chat(data):
    try:
        user_id = data.get('user_id')
        if user_id and user_id in active_connections:
            if request.sid in active_connections[user_id]:
                active_connections[user_id].remove(request.sid)
            if not active_connections[user_id]:
                del active_connections[user_id]
        
        socketio.server.leave_room(request.sid, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка при отключении от чата: {e}")


if __name__ == '__main__':
    update_thread = threading.Thread(target=process_telegram_updates, daemon=True)
    update_thread.start()
    
    logger.info(f"Сервер запущен на {SERVER_HOST}:{SERVER_PORT}")
    socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, debug=False, allow_unsafe_werkzeug=True)

