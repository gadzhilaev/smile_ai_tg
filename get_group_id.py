"""
Вспомогательный скрипт для получения ID группы.
Запустите этот скрипт после того, как добавите бота в группу и отправите сообщение.
"""
import requests
from config import BOT_TOKEN

if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
    print("❌ Ошибка: BOT_TOKEN не установлен в .env файле")
    print("Пожалуйста, установите токен бота в файле .env")
    exit(1)

api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

print("🔍 Получаю обновления от Telegram...")
print("💡 Убедитесь, что вы добавили бота в группу и отправили сообщение в группу\n")

try:
    response = requests.get(f"{api_url}/getUpdates", timeout=10)
    response.raise_for_status()
    result = response.json()
    
    if not result.get("ok"):
        print(f"❌ Ошибка: {result}")
        exit(1)
    
    updates = result.get("result", [])
    
    if not updates:
        print("⚠️  Обновлений не найдено.")
        print("Попробуйте:")
        print("1. Добавить бота в группу")
        print("2. Отправить любое сообщение в группу")
        print("3. Запустить этот скрипт снова")
        exit(0)
    
    print("📋 Найденные чаты:\n")
    
    found_groups = []
    for update in updates:
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_type = chat.get("type")
        chat_id = chat.get("id")
        chat_title = chat.get("title", "Без названия")
        
        if chat_type == "group" or chat_type == "supergroup":
            if chat_id not in [g["id"] for g in found_groups]:
                found_groups.append({
                    "id": chat_id,
                    "title": chat_title,
                    "type": chat_type
                })
    
    if found_groups:
        print("✅ Найдены группы:\n")
        for group in found_groups:
            print(f"📌 Название: {group['title']}")
            print(f"   ID: {group['id']}")
            print(f"   Тип: {group['type']}")
            print()
        
        print("💡 Скопируйте ID группы и вставьте его в .env файл как GROUP_CHAT_ID")
    else:
        print("⚠️  Группы не найдены в обновлениях.")
        print("Попробуйте отправить сообщение в группу и запустить скрипт снова.")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Ошибка при запросе к Telegram API: {e}")
    print("Проверьте правильность BOT_TOKEN в .env файле")
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")

