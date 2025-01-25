from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import json
import boto3
import logging

from flask import Flask, request

# Конфігурація
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Токен бота
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Назва каналу
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # S3 бакет
S3_FILE_KEY = "telegram_posts.json"
AWS_REGION = os.getenv("AWS_REGION")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL вашого сервера (наприклад, Heroku або інший хостинг)

# Ініціалізація S3
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

# Обробник команди /safe
async def safe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Отримана команда /safe.")
    await update.message.reply_text("Збереження повідомлень розпочато.")
    download_from_s3()
    upload_to_s3()
    await update.message.reply_text("Повідомлення успішно збережено.")

# Обробка оновлень із Telegram
async def process_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Отримано оновлення: {update}")

    if update.channel_post and update.channel_post.chat.username == CHANNEL_USERNAME:
        text = update.channel_post.text
        logger.info(f"Отримано пост з каналу: {text}")

        # Завантаження файлу з S3
        download_from_s3()
        try:
            with open(LOCAL_FILE, "r", encoding="utf-8") as file:
                posts = json.load(file)
        except json.JSONDecodeError:
            posts = []

        posts.append(text)

        # Збереження нового файлу
        with open(LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump(posts, file, ensure_ascii=False, indent=4)

        upload_to_s3()

# Запуск бота з Webhook
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Додаємо обробники
    application.add_handler(CommandHandler("safe", safe))

    # Flask сервер для Webhook
    app = Flask(__name__)

    @app.route("/webhook", methods=["POST"])
    def webhook():
        data = request.json
        application.update_queue.put(data)
        return {"ok": True}

    # Встановлення Webhook
    logger.info("Встановлення Webhook...")
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # Запуск Flask сервера
    port = int(os.getenv("PORT", 8443))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
