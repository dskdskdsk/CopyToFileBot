from quart import Quart, request, jsonify
import logging
from telegram import Update
from telegram.ext import Application
import asyncio

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

# Підключення до Telegram бота
async def process_update(data):
    # Використовуємо дані з вебхука
    application = Application.builder().token('YOUR_BOT_TOKEN').build()
    await application.update_queue.put(data)

@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        data = await request.get_json()  # Використовуємо асинхронну обробку даних
        if data:
            logger.info(f"Отримано дані: {data}")
            await process_update(data)
        else:
            logger.warning("Запит не містить даних.")
        
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Помилка обробки запиту: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# Запуск Quart серверу через uvicorn
if __name__ == "__main__":
    from uvicorn import run
    logger.info("Запуск сервера через uvicorn...")
    run(app, host="0.0.0.0", port=8443)
