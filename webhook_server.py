from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Отримано дані: {data}")
    # Логіка обробки повідомлень
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)  # Для Heroku порт буде автоматично змінюватися
