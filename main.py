import os
import requests
import time
from flask import Flask, request

# === 1. НАСТРОЙКИ ===
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

# === 2. ВЕБ-СЕРВЕР ДЛЯ RENDER ===
@app.route('/')
def home():
    return "🤖 DeVox Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if not update: return "ok", 200
        
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "")
            
            if text == "/start":
                send_message(chat_id, "🐺 Привет! Я DeVox. Бот работает.")
                send_animation(chat_id, "BAACAgIAAxkBAAMCaeFdUzN5tNI4r_mKJW--H3KYSQQAArqfAAJFDQlLzyLg1y5Hj4I7BA")
            elif text == "/test":
                send_animation(chat_id, "BAACAgIAAxkBAAMEaeFgf2cGLcUKtepNlq8U750S0FUAAs6VAALAcAlLsK2BDzM-K1M7BA")
            else:
                send_message(chat_id, f"Ты написал: {text}")
        return "ok", 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return "error", 500

# === 3. ФУНКЦИИ TELEGRAM ===
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_animation(chat_id, animation_id):
    url = f"{BASE_URL}/sendAnimation"
    payload = {"chat_id": chat_id, "animation": animation_id}
    response = requests.post(url, json=payload)
    print(f"Отправка анимации: {response.status_code}")

# === 4. ЗАПУСК ===
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print("🤖 Тестовый бот запущен!")
    app.run(host='0.0.0.0', port=port)
