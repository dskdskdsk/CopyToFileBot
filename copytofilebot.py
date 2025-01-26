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

# Назва файлу на S3
FILE_NAME = "telegram_messages.json"

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

# Функція для отримання існуючих повідомлень з S3
def load_messages_from_s3():
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=FILE_NAME)
        content = response['Body'].read().decode('utf-8')
        print(f"Файл {FILE_NAME} завантажено з S3.")
        return json.loads(content)  # Повертаємо список повідомлень
    except s3.exceptions.NoSuchKey:
        print(f"Файл {FILE_NAME} не знайдено, створюємо новий.")
        return []  # Якщо файл не існує, повертаємо порожній список

# Функція для збереження повідомлень на S3
def save_messages_to_s3(messages):
    try:
        json_data = json.dumps(messages, ensure_ascii=False, indent=4)
        s3.put_object(Bucket=S3_BUCKET, Key=FILE_NAME, Body=json_data)
        print(f"Файл {FILE_NAME} успішно оновлено на S3.")
    except Exception as e:
        print(f"Помилка при збереженні на S3: {e}")

# Основний цикл для додавання повідомлень
def save_to_s3(message_id, content, date):
    messages = load_messages_from_s3()  # Завантажуємо існуючі повідомлення
    new_message = {
        "message_id": message_id,
        "content": content,
        "date": date,
    }
    messages.append(new_message)  # Додаємо нове повідомлення
    save_messages_to_s3(messages)  # Зберігаємо оновлений список на S3

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
