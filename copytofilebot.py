from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
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
        logger.info(f"Починається завантаження файлу {LOCAL_FILE} на S3...")
        s3_client.upload_file(LOCAL_FILE, S3_BUCKET_NAME, S3_FILE_KEY)
        logger.info(f"Файл {LOCAL_FILE} успішно завантажено до S3.")
    except Exception as e:
        logger.error(f"Помилка під час завантаження до S3: {e}")

# Перевірка нових постів на каналі
def check_new_posts():
    try:
        # Отримуємо повідомлення з каналу
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url)
        data = response.json()

        # Якщо є нові повідомлення
        if data["ok"] and data["result"]:
            new_posts = []
            for message in data["result"]:
                if message.get("message") and message["message"].get("chat") and message["message"]["chat"]["username"] == CHANNEL_USERNAME:
                    new_posts.append(message["message"]["text"])

            # Якщо є нові пости
            if new_posts:
                download_from_s3()
                try:
                    with open(LOCAL_FILE, "r", encoding="utf-8") as file:
                        posts = json.load(file)
                except json.JSONDecodeError:
                    posts = []

                posts.extend(new_posts)

                with open(LOCAL_FILE, "w", encoding="utf-8") as file:
                    json.dump(posts, file, ensure_ascii=False, indent=4)

                logger.info(f"Нове повідомлення додано. Збережено {len(new_posts)} повідомлень.")
                upload_to_s3()
            else:
                logger.info("Нових повідомлень немає.")
        else:
            logger.warning("Не вдалося отримати повідомлення з каналу.")
    except Exception as e:
        logger.error(f"Помилка при перевірці нових постів: {e}")

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

    # Перевірка нових постів кожні 12 годин (43200 секунд)
    application.job_queue.run_repeating(check_new_posts, interval=43200, first=0)

    logger.info("Бот запущений.")
    application.run_polling()

if __name__ == "__main__":
    main()
