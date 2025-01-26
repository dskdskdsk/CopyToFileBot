import os
import json
import requests
import boto3
from datetime import datetime

# Завантаження змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

# Назва вашого Telegram-каналу
CHAT_ID = "@thisisofshooore"  # Замініть на username вашого каналу

# Перевірка наявності змінних середовища
if not all([BOT_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET]):
    raise ValueError("Одне або більше змінних середовища відсутнє!")

# Налаштування клієнта Amazon S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Функція для отримання оновлень
def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    response = requests.get(url, params=params)
    return response.json()

# Функція для збереження повідомлення у форматі JSON на S3
def save_to_s3(message_id, content, date):
    file_name = f"telegram_message_{message_id}.json"
    data = {
        "message_id": message_id,
        "content": content,
        "date": date,
    }
    # Перетворюємо дані в JSON-формат
    json_data = json.dumps(data, ensure_ascii=False, indent=4)
    # Зберігаємо на S3
    s3.put_object(Bucket=S3_BUCKET, Key=file_name, Body=json_data)
    print(f"Збережено: {file_name}")

# Основний цикл
def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            message = update.get("message")
            if message and "text" in message:
                message_id = message["message_id"]
                content = message["text"]
                # Конвертація дати у зручний формат
                date = datetime.utcfromtimestamp(message["date"]).strftime('%Y-%m-%d %H:%M:%S')
                save_to_s3(message_id, content, date)
            offset = update["update_id"] + 1

if __name__ == "__main__":
    main()
