from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
import requests
import json
import boto3
import logging
import os

# Конфігурація
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Вказуємо змінну середовища для токену
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Вказуємо змінну середовища для каналу
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # Вказуємо змінну середовища для S3 бакету
S3_FILE_KEY = "telegram_posts.json"  # Ключ файлу на S3
AWS_REGION = os.getenv("AWS_REGION")  # Вказуємо змінну середовища для регіону AWS

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

# Функція для перевірки нових постів в каналі
async def check_new_posts(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Перевірка нових постів у каналі.")
    download_from_s3()
    # Твоя логіка для перевірки нових постів у каналі
    # Наприклад, використовуючи Telegram API для отримання останніх постів з каналу
    upload_to_s3()

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

    # Ініціалізація JobQueue для періодичного виконання
    job_queue = application.job_queue

    # Додаємо задачу для періодичного виклику перевірки нових постів (наприклад, кожні 12 годин)
    job_queue.run_repeating(check_new_posts, interval=43200, first=0)  # 300 секунд = 5 хвилин

    # Команди
    application.add_handler(CommandHandler("safe", safe))

    logger.info("Бот запущений.")
    application.run_polling()

if __name__ == "__main__":
    main()
