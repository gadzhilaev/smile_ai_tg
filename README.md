# Telegram Support Bot Server

Сервер для обработки сообщений поддержки через Telegram бота. Принимает запросы от мобильного приложения, пересылает их в Telegram группу и отправляет push уведомления при ответах.

## Функционал

- Прием сообщений и фото от мобильного приложения
- Отправка сообщений в Telegram группу
- Push уведомления через Firebase Cloud Messaging (FCM)
- История переписок в SQLite
- WebSocket для обновления чата в реальном времени
- Автоматическое приветственное сообщение (раз в день)

## Установка

1. Создайте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env`:
```bash
cp .env.example .env
```

4. Настройте `.env`:
```
BOT_TOKEN=your_telegram_bot_token
GROUP_CHAT_ID=your_group_chat_id
SERVER_PORT=5000
SERVER_HOST=0.0.0.0
FCM_SERVICE_ACCOUNT_PATH=firebase-service-account.json
```

5. Получите `firebase-service-account.json`:
   - Firebase Console → Project Settings → Service Accounts
   - Generate New Private Key
   - Сохраните как `firebase-service-account.json` в корне проекта

## Запуск

```bash
source venv/bin/activate
python server.py
```

Сервер запустится на `http://0.0.0.0:5000`

## API Endpoints

### POST /send_message
Отправка сообщения с поддержкой фото.

**Multipart/form-data:**
- `user_id` (обязательно)
- `message` (обязательно)
- `user_name` (опционально)
- `photo` (опционально, можно несколько)

**JSON:**
```json
{
  "user_id": "123456789",
  "user_name": "Имя",
  "message": "Текст",
  "photo_url": "https://..." 
}
```

**Ответ:**
```json
{
  "success": true,
  "message_id": 12345,
  "photo_url": "/uploads/file.jpg",
  "photo_count": 1
}
```

### POST /register_device
Регистрация FCM токена устройства.

**JSON:**
```json
{
  "user_id": "123456789",
  "fcm_token": "fcm_token_here",
  "platform": "android",
  "device_id": "device_123"
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Устройство зарегистрировано успешно",
  "device_count": 1
}
```

### GET /message_history/<user_id>
Получение истории переписки.

**Query параметры:**
- `limit` (по умолчанию 50)
- `user_name` (для приветственного сообщения)

**Ответ:**
```json
{
  "success": true,
  "messages": [
    {
      "message": "Текст",
      "photo_url": "/uploads/file.jpg",
      "direction": "user",
      "created_at": "2024-01-01 12:00:00"
    }
  ],
  "greeting_sent": false
}
```

### GET /health
Проверка работоспособности.

**Ответ:**
```json
{
  "status": "ok"
}
```

### GET /check_device/<user_id>
Проверка регистрации устройства.

**Ответ:**
```json
{
  "user_id": "123456789",
  "registered": true,
  "device_count": 1,
  "has_tokens": true
}
```

### GET /uploads/<filename>
Получение загруженных файлов.

## WebSocket Events

### Подключение
```javascript
socket.emit('join_chat', { user_id: 'user_123' });
```

### Отключение
```javascript
socket.emit('leave_chat', { user_id: 'user_123' });
```

### События
- `new_message` - новое сообщение в чате
- `joined` - подтверждение подключения
- `error` - ошибка

## Интеграция с Rust сервером

### HTTP Proxy

Rust сервер может проксировать запросы к этому серверу:

```rust
// Пример для actix-web
async fn send_support_message(
    req: web::Json<SupportMessage>,
) -> Result<HttpResponse, Error> {
    let client = reqwest::Client::new();
    
    let response = client
        .post("http://localhost:5000/send_message")
        .json(&req.into_inner())
        .send()
        .await?;
    
    Ok(HttpResponse::Ok().json(response.json().await?))
}
```

### Прямое использование API

Все endpoints доступны через HTTP. Rust сервер может:

1. **Проксировать запросы** - принимать запросы от клиентов и пересылать на этот сервер
2. **Использовать как микросервис** - вызывать API напрямую из Rust кода
3. **WebSocket прокси** - проксировать WebSocket соединения

### Пример интеграции

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct SupportMessage {
    user_id: String,
    message: String,
    user_name: Option<String>,
}

async fn forward_to_support_bot(
    client: &Client,
    message: SupportMessage,
) -> Result<(), Box<dyn std::error::Error>> {
    let response = client
        .post("http://localhost:5000/send_message")
        .json(&message)
        .send()
        .await?;
    
    let result: serde_json::Value = response.json().await?;
    println!("Support bot response: {:?}", result);
    
    Ok(())
}
```

### WebSocket интеграция

```rust
use tokio_tungstenite::{connect_async, tungstenite::Message};

async fn connect_support_websocket(user_id: &str) {
    let url = "ws://localhost:5000/socket.io/?EIO=4&transport=websocket";
    let (ws_stream, _) = connect_async(url).await.unwrap();
    
    // Отправка join_chat
    let join_msg = serde_json::json!({
        "event": "join_chat",
        "data": {"user_id": user_id}
    });
    // ... обработка сообщений
}
```

## Структура проекта

```
smile_ai_tg/
├── server.py              # Flask сервер
├── bot.py                 # Telegram Bot API
├── database.py            # SQLite база данных
├── push_notifications.py  # FCM push уведомления
├── config.py             # Конфигурация
├── requirements.txt      # Зависимости
├── .env                  # Настройки
└── uploads/              # Загруженные файлы
```

## База данных

SQLite база `support_bot.db` с таблицами:
- `messages` - история сообщений
- `device_tokens` - FCM токены устройств
- `message_mapping` - связь Telegram message_id с user_id
- `greetings_sent` - отслеживание отправленных приветствий

## Приветственное сообщение

Приветственное сообщение отправляется автоматически:
- При первом запросе истории за день
- Только один раз в день для каждого пользователя
- Формат: "Здравствуйте, {user_name}!" или "Здравствуйте!"

## Безопасность

- Не коммитьте `.env` и `firebase-service-account.json`
- Для продакшена используйте HTTPS
- Добавьте аутентификацию для API
- Настройте rate limiting

## Troubleshooting

**Бот не отправляет сообщения:**
- Проверьте `BOT_TOKEN` и `GROUP_CHAT_ID`
- Убедитесь, что бот добавлен в группу

**Push не работают:**
- Проверьте `firebase-service-account.json`
- Убедитесь, что устройство зарегистрировано
- Проверьте логи сервера

**Фото не загружаются:**
- Проверьте права на директорию `uploads/`
- Максимальный размер файла: 10MB
