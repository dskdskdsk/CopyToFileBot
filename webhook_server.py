from flask import Flask, request, jsonify
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Отримання даних з запиту
        data = request.json
        if data:
            logger.info(f"Отримано дані: {data}")
        else:
            logger.warning("Запит не містить даних.")
        
        # Логіка обробки повідомлень (наприклад, якщо це пост з каналу)
        # Тут додай свою логіку для обробки даних
        
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Помилка обробки запиту: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)  # Для Heroku порт буде автоматично змінюватися
