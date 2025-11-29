# Быстрый старт

## 1. Настройка окружения

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Установите зависимости (если еще не установлены)
pip install -r requirements.txt
```

## 2. Настройка .env файла

```bash
# Скопируйте пример
cp .env.example .env

# Откройте .env и заполните:
# - BOT_TOKEN (получите у @BotFather)
# - GROUP_CHAT_ID (используйте get_group_id.py)
```

### Минимальная настройка (без push уведомлений):

```env
BOT_TOKEN=your_bot_token_here
GROUP_CHAT_ID=your_group_chat_id_here
```

### Полная настройка (с push уведомлениями):

Добавьте также настройки для FCM (Android) и/или APNs (iOS) - см. README.md

## 3. Получение ID группы

```bash
# Добавьте бота в группу и отправьте сообщение
# Затем запустите:
python get_group_id.py
```

## 4. Запуск

```bash
python server.py
```

Сервер запустится на `http://0.0.0.0:5000`

## 5. Тестирование

### Проверка работоспособности:
```bash
curl http://localhost:5000/health
```

### Отправка тестового сообщения:
```bash
curl -X POST http://localhost:5000/send_message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "message": "Тестовое сообщение"
  }'
```

## 6. Интеграция с мобильным приложением

См. [MOBILE_API.md](MOBILE_API.md) для подробной документации API.

## Что дальше?

1. Настройте push уведомления (FCM для Android, APNs для iOS)
2. Интегрируйте API в мобильное приложение
3. Протестируйте полный цикл: отправка сообщения → ответ в группе → push уведомление

