# Быстрый старт

Краткая инструкция по запуску сервера поддержки.

## 1. Настройка

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Создайте файл .env
cp .env.example .env

# Откройте .env и заполните:
# - BOT_TOKEN (получите у @BotFather в Telegram)
# - GROUP_CHAT_ID (используйте get_group_id.py)
# - FCM_SERVER_KEY (из Firebase Console)
```

## 2. Получение ID группы

```bash
# Добавьте бота в группу и отправьте сообщение
# Затем запустите:
python get_group_id.py
```

## 3. Запуск сервера

```bash
python server.py
```

Сервер запустится на `http://0.0.0.0:5000`

## 4. Тестирование

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
    "user_name": "Тестовый пользователь",
    "message": "Тестовое сообщение"
  }'
```

## 5. Интеграция в Flutter

См. подробную инструкцию в [FLUTTER_GUIDE.md](FLUTTER_GUIDE.md)

## Важно

- Убедитесь, что бот добавлен в группу поддержки
- Проверьте, что FCM_SERVER_KEY правильный
- Для продакшена используйте HTTPS и настройте аутентификацию

