from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
import json
import boto3
import logging
from fastapi import FastAPI, Request
import uvicorn

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
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ім'я локального файлу
LOCAL_FILE = "telegram_posts.json"

# Завантаження файлу з S3 або створення нового
def download_from_s3():
    logger.info("Спроба завантажити файл із S3...")
    try:
        logger.debug(f"Завантаження файлу {S3_FILE_KEY} з бакету {S3_BUCKET_NAME}.")
        s3_client.download_file(S3_BUCKET_NAME, S3_FILE_KEY, LOCAL_FILE)
        logger.info("Файл успішно завантажено з S3.")
    except Exception as e:
        logger.warning(f"Не вдалося завантажити файл з S3: {e}")
        with open(LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump([], file)
        logger.info("Створено новий файл для збереження даних.")

# Збереження файлу до S3
def upload_to_s3():
    logger.info("Спроба завантажити файл до S3...")
    try:
        logger.debug(f"Завантаження файлу {LOCAL_FILE} до бакету {S3_BUCKET_NAME} під ключем {S3_FILE_KEY}.")
        s3_client.upload_file(LOCAL_FILE, S3_BUCKET_NAME, S3_FILE_KEY)
        logger.info("Файл успішно завантажено до S3.")
    except Exception as e:
        logger.error(f"Помилка під час завантаження до S3: {e}")

# Обробник команди /safe
async def safe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Отримано команду /safe.")
    try:
        await update.message.reply_text("Збереження повідомлень розпочато.")
        download_from_s3()
        upload_to_s3()
        await update.message.reply_text("Повідомлення успішно збережено.")
    except Exception as e:
        logger.error(f"Помилка в команді /safe: {e}")

# Обробка оновлень із Telegram
async def process_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Отримано нове оновлення.")
    logger.debug(f"Повні дані оновлення: {update.to_dict()}")

    if update.channel_post:
        logger.debug(f"Оновлення отримано з каналу: {update.channel_post.chat.username}.")
        if update.channel_post.chat.username == CHANNEL_USERNAME:
            text = update.channel_post.text
            logger.info(f"Повідомлення з каналу {CHANNEL_USERNAME}: {text}")

            # Завантаження файлу з S3
            download_from_s3()
            try:
                with open(LOCAL_FILE, "r", encoding="utf-8") as file:
                    posts = json.load(file)
                logger.debug("Файл успішно завантажено у пам'ять.")
            except json.JSONDecodeError as e:
                posts = []
                logger.warning(f"Файл з постами порожній або має помилки у форматуванні: {e}")

            posts.append(text)
            logger.debug(f"Додано нове повідомлення до списку. Загальна кількість постів: {len(posts)}")

            # Збереження нового файлу
            with open(LOCAL_FILE, "w", encoding="utf-8") as file:
                json.dump(posts, file, ensure_ascii=False, indent=4)
            logger.info("Повідомлення успішно збережено до локального файлу.")

            upload_to_s3()
        else:
            logger.warning(f"Отримано повідомлення з нецільового каналу: {update.channel_post.chat.username}")
    else:
        logger.warning("Оновлення не є повідомленням з каналу.")

# Ініціалізація FastAPI сервера
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    logger.info("Отримано запит через webhook.")
    try:
        update_data = await request.json()
        logger.debug(f"Дані запиту: {update_data}")
        update = Update.de_json(update_data, application.bot)
        logger.debug(f"Оновлення перетворено: {update.to_dict()}")
        await application.update_queue.put(update)
    except Exception as e:
        logger.error(f"Помилка обробки webhook: {e}")
    return {"ok": True}

# Запуск бота з Webhook
async def main():
    global application
    logger.info("Ініціалізація бота.")
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Додаємо обробники
        logger.info("Додавання обробників.")
        application.add_handler(CommandHandler("safe", safe))
        application.add_handler(MessageHandler(filters.ChannelPost, process_update))

        # Встановлення Webhook
        logger.info("Встановлення Webhook...")
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

        # Запуск FastAPI сервера через uvicorn
        logger.info("Запуск FastAPI сервера через uvicorn...")
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8443)))
    except Exception as e:
        logger.error(f"Помилка під час запуску програми: {e}")

if __name__ == "__main__":
    logger.info("Запуск програми...")
    import asyncio
    asyncio.run(main())
