import requests
import json
import time

BOT_TOKEN = "8183666502:AAH0_aOuAgHzU5T5RydUwHXj9L-SNBYCQ6k"  # Встав свій токен
CHANNEL_ID = "@thisisofshooore"  # Назва каналу (або ID, якщо приватний)
OUTPUT_FILE = "telegram_posts.json"  # Ім'я файлу для збереження

def fetch_posts(offset=None):
    """Отримати нові повідомлення з Telegram-каналу."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 10}
    response = requests.get(url, params=params)
    return response.json()

def save_posts(messages):
    """Зберегти повідомлення у файл."""
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
        for message in messages:
            if "text" in message:  # Перевіряємо, чи є текст у повідомленні
                formatted_message = {
                    "post_id": message["message_id"],
                    "channel_id": CHANNEL_ID,
                    "text": message["text"],
                    "date": message["date"]
                }
                json.dump(formatted_message, file, ensure_ascii=False)
                file.write("\n")

def main():
    """Основний цикл для отримання нових постів."""
    print("Бот запущено...")
    last_update_id = None

    while True:
        data = fetch_posts(offset=last_update_id)
        if data.get("ok"):
            for update in data["result"]:
                last_update_id = update["update_id"] + 1
                if "message" in update:  # Перевіряємо, чи це повідомлення
                    save_posts([update["message"]])
                    print(f"Збережено повідомлення: {update['message'].get('text', 'Без тексту')}")

        time.sleep(5)  # Перевіряємо канал кожні 5 секунд

if __name__ == "__main__":
    main()
