import os
import json
import hashlib
import requests
import boto3
from datetime import datetime
import logging

# Завантаження змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")  # Ваш Telegram ID

# Назва вашого Telegram-каналу
CHAT_ID = "@thisisofshooore"  # Замініть на username вашого каналу

# Перевірка наявності змінних середовища
if not all([BOT_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, ADMIN_USER_ID]):
    raise ValueError("Одне або більше змінних середовища відсутнє!")

# Налаштування клієнта Amazon S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Файл, в який зберігаються всі пости
FILE_NAME = "telegram_messages.json"

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Завантаження існуючих повідомлень з S3
def load_messages_from_s3():
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=FILE_NAME)
        content = response["Body"].read().decode("utf-8")
        logging.info("Файл з повідомленнями успішно завантажено з S3.")
        return json.loads(content)  # Повертаємо список повідомлень
    except s3.exceptions.NoSuchKey:
        logging.warning(f"Файл {FILE_NAME} не знайдено на S3, створюється новий.")
        return []  # Якщо файл не існує, повертаємо порожній список

# Збереження повідомлень на S3
def save_messages_to_s3(messages):
    try:
        json_data = json.dumps(messages, ensure_ascii=False, indent=4)
        s3.put_object(Bucket=S3_BUCKET, Key=FILE_NAME, Body=json_data)
        logging.info(f"Файл {FILE_NAME} оновлено на S3.")
    except Exception as e:
        logging.error(f"Помилка при збереженні на S3: {e}")

# Генерація хешу для кожного повідомлення
def generate_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

# Основна функція для отримання нових повідомлень
def fetch_and_save_updates():
    logging.info("Початок перевірки нових повідомлень...")
    
    # Завантажуємо існуючі повідомлення з S3
    messages = load_messages_from_s3()
    known_hashes = {msg["hash"] for msg in messages}  # Хеші існуючих повідомлень
    offset = max((msg["message_id"] for msg in messages), default=None)  # Останній message_id
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset + 1 if offset else None, "timeout": 30}
    
    try:
        response = requests.get(url, params=params).json()
        logging.info("Отримано оновлення від Telegram.")
    except Exception as e:
        logging.error(f"Помилка при отриманні оновлень від Telegram: {e}")
        return

    new_messages = []
    for update in response.get("result", []):
        message = update.get("message")
        if not message or "text" not in message:
            continue

        content = message["text"]
        message_id = message["message_id"]
        date = datetime.utcfromtimestamp(message["date"]).strftime("%Y-%m-%d %H:%M:%S")
        hash_value = generate_hash(content)

        if hash_value in known_hashes:
            logging.info(f"Пропущено дубль повідомлення ID {message_id}.")
            continue

        new_message = {
            "message_id": message_id,
            "content": content,
            "date": date,
            "hash": hash_value,
        }
        new_messages.append(new_message)
        logging.info(f"Новий пост додано: {content[:30]}...")

    if new_messages:
        messages.extend(new_messages)
        save_messages_to_s3(messages)
        logging.info(f"Додано {len(new_messages)} нових повідомлень.")
    else:
        logging.info("Нових повідомлень не знайдено.")

# Функція для обробки команд в Telegram
def handle_telegram_commands(update):
    chat_id = update["message"]["chat"]["id"]
    text = update["message"]["text"]
    
    if str(chat_id) != ADMIN_USER_ID:
        logging.warning(f"Неавторизований доступ: {chat_id}")
        return

    if text == "/save":
        logging.info("Команда /save отримана. Виконую збереження повідомлень...")
        fetch_and_save_updates()
        send_message(chat_id, "Збереження нових повідомлень завершено.")

# Функція для відправки повідомлень через Telegram
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": chat_id, "text": text}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            logging.info(f"Повідомлення надіслано користувачу {chat_id}.")
        else:
            logging.error(f"Не вдалося надіслати повідомлення користувачу {chat_id}: {response.text}")
    except Exception as e:
        logging.error(f"Помилка при відправці повідомлення користувачу {chat_id}: {e}")

# Отримання оновлень і перевірка команд
def check_for_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        updates = response.json().get("result", [])
        for update in updates:
            handle_telegram_commands(update)
    except Exception as e:
        logging.error(f"Помилка при отриманні оновлень команд: {e}")

if __name__ == "__main__":
    check_for_commands()  # Перевірка на нові команди
