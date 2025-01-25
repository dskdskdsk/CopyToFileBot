from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler
from telegram.ext import filters
import os
import json
import boto3
import logging
from fastapi import FastAPI, Request
import uvicorn

BOT_TOKEN = "7779435652:AAG68Xg1ZkPIBa1AkBZxL8BguszLRxA1I1I"  # Токен бота
CHANNEL_USERNAME = "thisisofshooore"  # Назва каналу
S3_BUCKET_NAME = "copytofilebot"  # Назва бакету S3
S3_FILE_KEY = "telegram_posts.json"
AWS_REGION = "us-east-2"  # Регион AWS

# Використання змінних середовища для AWS ключів
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise ValueError("AWS credentials are not set in the environment.")
    
WEBHOOK_URL = "https://copytofilebot-a33c9815052b.herokuapp.com"  # URL вашого сервера
PORT = 8000

# Ініціалізація S3
s3_client = boto3.client(
    "s3", 
    region_name=AWS_REGION, 
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Логування
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ім'я локального файлу
LOCAL_FILE = "telegram_posts.json"

# Завантаження файлу з S3 або створення нового
def download_from_s3():
    try:
        logger.debug(f"Спроба завантажити файл {S3_FILE_KEY} з S3...")
        s3_client.download_file(S3_BUCKET_NAME, S3_FILE_KEY, LOCAL_FILE)
        logger.info(f"Файл {S3_FILE_KEY} завантажено з S3.")
    except Exception as e:
        logger.warning(f"Не вдалося завантажити файл з S3: {e}. Буде створено новий.")
        with open(LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump([], file)

# Збереження файлу до S3
def upload_to_s3():
    try:
        logger.debug(f"Спроба завантажити файл {LOCAL_FILE} до S3...")
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
    
    if update.channel_post:
        logger.debug(f"Перевірка отриманого каналу: {update.channel_post.chat.username}")
        if update.channel_post.chat.username == CHANNEL_USERNAME:
            text = update.channel_post.text
            logger.info(f"Отримано пост з каналу {CHANNEL_USERNAME}: {text}")

            # Завантаження файлу з S3
            download_from_s3()
            try:
                with open(LOCAL_FILE, "r", encoding="utf-8") as file:
                    posts = json.load(file)
            except json.JSONDecodeError:
                posts = []
                logger.warning("Файл з постами порожній або має помилки в форматуванні.")

            posts.append(text)

            # Збереження нового файлу
            with open(LOCAL_FILE, "w", encoding="utf-8") as file:
                json.dump(posts, file, ensure_ascii=False, indent=4)

            upload_to_s3()
        else:
            logger.warning(f"Отримано пост від нецільового каналу: {update.channel_post.chat.username}")
    else:
        logger.warning("Отримано повідомлення, яке не є каналом.")

# Ініціалізація FastAPI серверу
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.debug(f"Отримано дані через webhook: {data}")
        update = Update.de_json(data, application.bot)
        logger.debug(f"Обробка оновлення: {update}")
        await application.update_queue.put(update)
    except Exception as e:
        logger.error(f"Помилка обробки webhook: {e}")
    return {"ok": True}

# Запуск бота
async def main():
    global application
    application = Application.builder().token(BOT_TOKEN).build()

    # Додавання обробників
    application.add_handler(CommandHandler("safe", safe))
    application.add_handler(MessageHandler(filters.ChannelPost, process_update))

    # Встановлення Webhook
    logger.info("Встановлення Webhook...")
    await application.bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/webhook")

    # Запуск FastAPI через Uvicorn
    logger.info("Запуск FastAPI через Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    # Запуск бота
    logger.info("Запуск бота...")
    import asyncio
    asyncio.run(main())
