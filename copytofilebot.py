import requests
import json
import boto3
import logging
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Конфігурація
BOT_TOKEN = os.getenv("8183666502:AAH0_aOuAgHzU5T5RydUwHXj9L-SNBYCQ6k")  # Токен бота, отриманий через BotFather
CHANNEL_USERNAME = os.getenv("@thisisofshooore")  # Username каналу (наприклад, "@назва_каналу")
S3_BUCKET_NAME = os.getenv("copytofilebot")  # Назва S3 бакету
S3_FILE_KEY = "telegram_posts.json"  # Ім'я файлу в бакеті S3
AWS_REGION = os.getenv("us-east-2")  # Наприклад, "us-east-1"

# Ініціалізація S3 клієнта
s3_client = boto3.client("s3", region_name=AWS_REGION)

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ім'я локального файлу
LOCAL_FILE = "telegram_posts.json"

# Завантаження файлу з S3 або створення нового
def download_from_s3():
    try:
        s3_client.download_file(S3_BUCKET_NAME, S3_FILE_KEY, LOCAL_FILE)
        logger.info(f"Файл {S3_FILE_KEY} завантажено з S3.")
    except Exception as e:
        logger.warning(f"Не вдалося завантажити файл з S3: {e}. Буде створено новий.")
        with open(LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump([], file)

# Збереження файлу до S3
def upload_to_s3():
    try:
        s3_client.upload_file(LOCAL_FILE, S3_BUCKET_NAME, S3_FILE_KEY)
        logger.info(f"Файл {LOCAL_FILE} успішно завантажено до S3.")
    except Exception as e:
        logger.error(f"Помилка під час завантаження до S3: {e}")

# Збереження повідомлень у файл
def save_messages(messages):
    try:
        if not os.path.exists(LOCAL_FILE):
            existing_messages = []
        else:
            with open(LOCAL_FILE, "r", encoding="utf-8") as file:
                existing_messages = json.load(file)

        existing_ids = {msg["message_id"] for msg in existing_messages}
        new_messages = [msg for msg in messages if msg["message_id"] not in existing_ids]

        if new_messages:
            logger.info(f"Збереження {len(new_messages)} нових повідомлень.")
            existing_messages.extend(new_messages)
            with open(LOCAL_FILE, "w", encoding="utf-8") as file:
                json.dump(existing_messages, file, ensure_ascii=False, indent=4)
            upload_to_s3()
        else:
            logger.info("Немає нових повідомлень для збереження.")
    except Exception as e:
        logger.error(f"Помилка при збереженні повідомлень: {e}")

# Команда /save для збереження постів вручну
def save_command(update: Update, context: CallbackContext):
    logger.info("Отримано команду /save від користувача.")
    try:
        # Імітуємо отримання повідомлень для прикладу
        example_messages = [
            {
                "message_id": 12345,
                "text": "Тестове повідомлення",
                "date": "2025-01-22T12:00:00",
            }
        ]
        save_messages(example_messages)
        update.message.reply_text("Повідомлення успішно збережено!")
    except Exception as e:
        logger.error(f"Помилка при виконанні команди /save: {e}")
        update.message.reply_text("Сталася помилка при збереженні повідомлень.")

# Команда /start для перевірки роботи бота
def start_command(update: Update, context: CallbackContext):
    logger.info("Отримано команду /start від користувача.")
    update.message.reply_text("Бот запущено. Використовуйте /save для збереження постів!")

# Основна функція для запуску бота
def main():
    logger.info("Запуск бота...")
    download_from_s3()

    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Реєструємо команди
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("save", save_command))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
