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
POSTS_FILE = "posts.json"   # Назва файлу для збереження всіх постів

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

# Завантаження постів з файлу
def load_posts_from_file():
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

# Збереження постів у файл
def save_posts_to_file(posts_data):
    try:
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts_data, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Усі пости успішно збережено в файл {POSTS_FILE}.")
    except Exception as e:
        print(f"[ERROR] Помилка при збереженні постів у файл {POSTS_FILE}: {e}")

# Додавання нового посту до списку з перевіркою на дублікати
def add_post_to_list(posts_data, message):
    message_id = message["message_id"]
    
    # Перевіряємо, чи вже є такий пост в списку
    for post in posts_data:
        if post["message_id"] == message_id:
            print(f"[INFO] Пост з ID={message_id} вже додано, пропускаємо.")
            return posts_data  # Повертаємо список без змін, якщо дубль
    
    # Якщо посту немає в списку, додаємо новий
    date = datetime.utcfromtimestamp(message["date"]).strftime('%Y-%m-%d %H:%M:%S')
    text = message.get("text", "")
    
    post = {
        "message_id": message_id,
        "date": date,
        "text": text,
        "processed": False
    }
    
    posts_data.append(post)
    print(f"[INFO] Пост з ID={message_id} додано в список.")
    return posts_data

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

    # Завантажуємо пости з файлу
    posts_data = load_posts_from_file()

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
            if message and "text" in message:
                message_id = message["message_id"]
                content = message["text"]
                date = datetime.utcfromtimestamp(message["date"]).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[INFO] Нове повідомлення: ID={message_id}, Дата={date}, Текст={content}")

                # Додаємо пост до списку, якщо він унікальний
                posts_data = add_post_to_list(posts_data, message)

            offset = update["update_id"] + 1
            print(f"[DEBUG] Новий OFFSET: {offset}")
            save_offset_to_s3(offset)  # Збереження OFFSET у S3

        # Збереження всіх постів в один файл
        save_posts_to_file(posts_data)

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
