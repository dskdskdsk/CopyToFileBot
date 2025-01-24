from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import json
import boto3
import logging
import os

# Конфігурація
BOT_TOKEN = os.getenv("8183666502:AAH0_aOuAgHzU5T5RydUwHXj9L-SNBYCQ6k")
CHANNEL_USERNAME = os.getenv("thisisofshooore")
S3_BUCKET_NAME = os.getenv("copytofilebot")
S3_FILE_KEY = "telegram_posts.json"
AWS_REGION = os.getenv("us-east-2")

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

# Команда /safe для збереження повідомлень
async def safe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Отримана команда /safe.")
    await update.message.reply_text("Збереження повідомлень розпочато.")
    download_from_s3()
    # Твоя логіка для збереження повідомлень
    upload_to_s3()
    await update.message.reply_text("Повідомлення успішно збережено.")

# Запуск бота
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Команди
    application.add_handler(CommandHandler("safe", safe))

    logger.info("Бот запущений.")
    application.run_polling()

if __name__ == "__main__":
    main()
