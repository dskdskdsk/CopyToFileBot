import hashlib
import boto3
import json
import os
import logging
from telethon import TelegramClient

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Telegram API доступ
API_ID = "23390151"
API_HASH = "69d820891b50ddcdcb9abb473ecdfc32"
#BOT_TOKEN = "your_bot_token"
CHANNEL_ID = "thisisofshooore"
OUTPUT_FILE = "telegram_posts.json"

# AWS S3 доступ
S3_BUCKET_NAME = "copytofilebot"
S3_FILE_KEY = "telegram_posts.json"

# Ініціалізація клієнта S3
s3_client = boto3.client("s3")

def generate_hash(text):
    """Генерує хеш для тексту поста."""
    hash_value = hashlib.md5(text.encode("utf-8")).hexdigest()
    logging.debug(f"Згенеровано хеш: {hash_value} для тексту: {text[:30]}...")
    return hash_value

async def fetch_all_messages(client):
    """Отримати всі повідомлення з каналу."""
    logging.info("Початок отримання повідомлень з каналу Telegram.")
    messages = []
    try:
        async for message in client.iter_messages(CHANNEL_ID):
            if message.text:
                msg_data = {
                    "message_id": message.id,
                    "text": message.text,
                    "date": str(message.date),
                    "hash": generate_hash(message.text)
                }
                messages.append(msg_data)
                logging.debug(f"Отримано повідомлення: {msg_data}")
        logging.info(f"Загалом отримано повідомлень: {len(messages)}")
    except Exception as e:
        logging.error(f"Помилка під час отримання повідомлень: {e}")
    return messages

def load_existing_messages():
    """Завантажити повідомлення з S3."""
    logging.info("Спроба завантаження існуючого файлу з S3.")
    try:
        s3_client.download_file(S3_BUCKET_NAME, S3_FILE_KEY, OUTPUT_FILE)
        logging.info(f"Файл {OUTPUT_FILE} успішно завантажено з S3.")
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            messages = json.load(file)
            logging.info(f"Завантажено повідомлень із файлу: {len(messages)}")
            return messages
    except Exception as e:
        logging.warning(f"Не вдалося завантажити файл {S3_FILE_KEY} з S3: {e}")
        return []

def save_messages_to_s3(messages):
    """Зберегти оновлені повідомлення в S3."""
    logging.info(f"Спроба збереження файлу {OUTPUT_FILE} в S3.")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(messages, file, ensure_ascii=False, indent=4)
        logging.info(f"Файл {OUTPUT_FILE} успішно оновлено локально.")
        s3_client.upload_file(OUTPUT_FILE, S3_BUCKET_NAME, S3_FILE_KEY)
        logging.info(f"Файл {OUTPUT_FILE} успішно завантажено в S3 як {S3_FILE_KEY}.")
    except Exception as e:
        logging.error(f"Помилка під час збереження файлу {OUTPUT_FILE} в S3: {e}")

async def sync_channel(client):
    """Синхронізація повідомлень."""
    logging.info("Початок синхронізації повідомлень.")
    try:
        # Отримуємо всі повідомлення з каналу
        current_messages = await fetch_all_messages(client)

        # Завантажуємо збережені повідомлення
        saved_messages = load_existing_messages()

        # Отримуємо ID повідомлень
        saved_message_ids = {msg["message_id"] for msg in saved_messages}
        current_message_ids = {msg["message_id"] for msg in current_messages}

        # Видаляємо повідомлення, яких більше немає в каналі
        updated_messages = [msg for msg in saved_messages if msg["message_id"] in current_message_ids]

        # Додаємо нові повідомлення
        for msg in current_messages:
            if msg["message_id"] not in saved_message_ids:
                updated_messages.append(msg)
                logging.info(f"Додано нове повідомлення: {msg}")

        # Зберігаємо оновлений список повідомлень
        save_messages_to_s3(updated_messages)
        logging.info("Синхронізація завершена успішно.")
    except Exception as e:
        logging.error(f"Помилка під час синхронізації: {e}")

async def main():
    """Основний цикл."""
    logging.info("Бот розпочав роботу.")
    client = TelegramClient("session_name", API_ID, API_HASH)
    try:
        async with client:
            await sync_channel(client)
        logging.info("Робота бота завершена успішно.")
    except Exception as e:
        logging.critical(f"Критична помилка в основному циклі: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
