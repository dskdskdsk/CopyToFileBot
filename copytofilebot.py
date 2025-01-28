import os
import json
import requests
import boto3
from datetime import datetime
import time

# Налаштування
BOT_TOKEN = os.getenv("BOT_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
CHAT_ID = "@thisisofshooore"  # Назва вашого Telegram-каналу
OFFSET_FILE = "offset.json"  # Назва файлу для збереження offset у S3
ALL_MESSAGES_FILE = "all_messages.json"  # Назва файлу для збереження всіх повідомлень

# Перевірка змінних середовища
if not all([BOT_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET]):
    raise ValueError("[ERROR] Відсутні обов'язкові змінні середовища!")

# Налаштування S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Завантаження offset із S3
def load_offset_from_s3():
    try:
        print(f"[DEBUG] Завантаження OFFSET із файлу {OFFSET_FILE} на S3...")
        response = s3.get_object(Bucket=S3_BUCKET, Key=OFFSET_FILE)
        offset_data = json.loads(response['Body'].read().decode('utf-8'))
        offset = offset_data.get("offset", 0)
        print(f"[INFO] Успішно завантажено OFFSET={offset} із S3.")
        return offset
    except s3.exceptions.NoSuchKey:
        print(f"[WARNING] Файл {OFFSET_FILE} не знайдено у S3. Використовується OFFSET=0.")
        return 0
    except Exception as e:
        print(f"[ERROR] Помилка при завантаженні OFFSET із S3: {e}")
        return 0

# Збереження offset у S3
def save_offset_to_s3(offset):
    try:
        print(f"[DEBUG] Збереження OFFSET={offset} у файл {OFFSET_FILE} на S3...")
        offset_data = json.dumps({"offset": offset})
        s3.put_object(Bucket=S3_BUCKET, Key=OFFSET_FILE, Body=offset_data)
        print(f"[INFO] OFFSET={offset} успішно збережено у S3.")
    except Exception as e:
        print(f"[ERROR] Помилка при збереженні OFFSET у S3: {e}")

# Завантаження всіх повідомлень з файлу
def load_all_messages():
    if os.path.exists(ALL_MESSAGES_FILE):
        with open(ALL_MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Збереження всіх повідомлень в файл
def save_all_messages(messages):
    try:
        with open(ALL_MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Усі повідомлення успішно збережено в файл {ALL_MESSAGES_FILE}.")
    except Exception as e:
        print(f"[ERROR] Помилка при збереженні повідомлень у файл: {e}")

# Отримання оновлень із Telegram API
def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    try:
        print(f"[DEBUG] Запит до Telegram API із offset={offset}...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"[INFO] Успішно отримано відповідь від Telegram API.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Помилка при запиті до Telegram API: {e}")
        return {"result": []}

# Основний цикл
def main():
    print("[INFO] Запуск програми для отримання повідомлень...")

    # Завантажуємо OFFSET із S3
    offset = load_offset_from_s3()

    # Завантажуємо всі існуючі повідомлення
    all_messages = load_all_messages()

    while True:
        updates = get_updates(offset)
        if not updates or "result" not in updates:
            print("[WARNING] Отримано некоректну відповідь від Telegram API.")
            time.sleep(5)
            continue

        results = updates.get("result", [])
        print(f"[INFO] Отримано {len(results)} оновлень.")
        for update in results:
            print(f"[DEBUG] Обробка оновлення: {update}")
            message = update.get("message")
            if message and "text" in message:  # Звичайні повідомлення
                message_id = message["message_id"]
                content = message["text"]
                date = datetime.utcfromtimestamp(message["date"]).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[INFO] Нове повідомлення: ID={message_id}, Дата={date}, Текст={content}")

                # Додаємо повідомлення до списку
                all_messages.append({
                    "message_id": message_id,
                    "date": message["date"],
                    "content": content,
                })

            # Обробка повідомлень типу 'channel_post' (пости з каналу)
            channel_post = update.get("channel_post")
            if channel_post and "text" in channel_post:  # Перевірка на наявність тексту
                post_id = channel_post["message_id"]
                content = channel_post["text"]
                date = datetime.utcfromtimestamp(channel_post["date"]).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[INFO] Нове повідомлення з каналу: ID={post_id}, Дата={date}, Текст={content}")

                # Додаємо пост до списку
                all_messages.append({
                    "message_id": post_id,
                    "date": channel_post["date"],
                    "content": content,
                })

            # Оновлюємо OFFSET
            offset = update["update_id"] + 1
            print(f"[DEBUG] Новий OFFSET: {offset}")
            save_offset_to_s3(offset)  # Збереження OFFSET у S3

        # Збереження всіх повідомлень в один файл
        save_all_messages(all_messages)

        # Невелика пауза перед наступним запитом
        time.sleep(1)


if __name__ == "__main__":
    try:
        print("[INFO] Запуск програми...")
        main()
    except KeyboardInterrupt:
        print("[INFO] Програму зупинено вручну.")
    except Exception as e:
        print(f"[ERROR] Невідома помилка: {e}")
