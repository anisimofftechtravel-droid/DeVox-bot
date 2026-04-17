import requests
import time
import math
import random
import re
import os
from flask import Flask, request

# ========== ПЕРЕМЕННЫЕ ИЗ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN")
YANDEX_GEO_KEY = os.environ.get("YANDEX_GEO_KEY")
GIS2_API_KEY = os.environ.get("GIS2_API_KEY")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_lang = {}
user_last_location = {}
user_taps = {}
user_has_location = {}

# ========== АНИМАЦИИ (СТАРАЯ РАБОЧАЯ СТРУКТУРА) ==========
animations = {
    "thinking": ["BAACAgIAAxkBAAIFOWnZZw09s7KrWkqDMw8aU29KBCd4AAJ4mwACXIjISpqd6_XuB4UaOwQ"],
    "pet_level_1": "BAACAgIAAxkBAAIFtmnZeQW0mj-A2L5QrkMxRmAAAZjqcAACqJMAAnQYoUoNOhJH5nPCEjsE",
    "pet_level_2": "BAACAgIAAyEFAASH3GjZAAICemnVoPJHTrJOisgOBqnkSiCPBzCQAALXnQAC-JWxSnfAxJuKO7a4OwQ",
    "pet_level_3": "BAACAgIAAxkBAAIFu2nZeZCKTOMcQNyTrN1Y8HHo6_lFAAKzmwACXIjISiN4C46JruovOwQ",
    "welcome": "BAACAgIAAxkBAAID-GnYEdDqQB8Fq-UtPuDK7xVL5DoeAAKJnAACvsrBSvR3HSULCjAkOwQ",
    "green_check": "BAACAgIAAxkBAAMDaeFfUtg_F7b1gDHGLoe_Q2Zmy1IAAvKlAAKAEwhLGU5iRq6tWhA7BA"
}

# ========== ВЕБ-СЕРВЕР ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 DeVox Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        
        if not update:
            return "ok", 200
        
        if "message" in update and "location" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            lat = update["message"]["location"]["latitude"]
            lon = update["message"]["location"]["longitude"]
            
            print(f"📍 Геопозиция от {chat_id}: {lat}, {lon}")
            
            if chat_id not in user_lang:
                user_lang[chat_id] = "ru"
            
            handle_location(chat_id, lat, lon)
            return "ok", 200
        
        if "message" in update:
            handle_message(update["message"])
        elif "callback_query" in update:
            cb = update["callback_query"]
            handle_callback(cb["message"]["chat"]["id"], cb["data"], cb["id"])
        
        return "ok", 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return "error", 500

def remove_keyboard(chat_id):
    """Убирает клавиатуру и отправляет анимацию вместо зелёной галочки"""
    # Отправляем анимацию (вместо зелёной галочки)
    send_video(chat_id, animations["green_check"])
    
    # Убираем клавиатуру
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "✅",
        "reply_markup": {"remove_keyboard": True}
    }
    try:
        requests.post(url, json=payload, timeout=30)
        print(f"🗑️ Клавиатура удалена для {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка удаления клавиатуры: {e}")

def send_message(chat_id, text, reply_markup=None, parse_mode="MarkdownV2"):
    url = f"{BASE_URL}/sendMessage"
    if parse_mode == "MarkdownV2":
        for ch in r'_*[]()~`>#+-=|{}.!':
            text = text.replace(ch, '\\' + ch)
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"📤 Сообщение отправлено: {response.status_code}")
        return response
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def send_video(chat_id, video_id):
    url = f"{BASE_URL}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_id}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print(f"✅ Видео отправлено: {video_id[:20]}...")
        else:
            print(f"❌ Ошибка видео: {response.status_code}")
        return response
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def send_random_thinking(chat_id):
    video_id = random.choice(animations["thinking"])
    send_video(chat_id, video_id)

def text_to_voice_yandex(text, chat_id, lang="ru"):
    if len(text) > 5000:
        text = text[:4997] + "..."
    clean_text = re.sub(r'[^\w\s\.\,\!\?\-\—\ ]', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    if len(clean_text) == 0:
        return False
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    data = {
        "text": clean_text,
        "lang": "ru-RU",
        "voice": "ermil",
        "emotion": "good",
        "speed": 1.0,
        "format": "oggopus"
    }
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        if response.status_code == 200:
            files = {"voice": ("voice.ogg", response.content, "audio/ogg")}
            send_result = requests.post(f"{BASE_URL}/sendVoice", data={"chat_id": chat_id}, files=files, timeout=30)
            return send_result.status_code == 200
        return False
    except:
        return False

def get_language_keyboard():
    return {"inline_keyboard": [[
        {"text": "🇷🇺 Русский", "callback_data": "lang_ru"},
        {"text": "🇬🇧 English", "callback_data": "lang_en"},
        {"text": "🇨🇳 中文", "callback_data": "lang_zh"}
    ]]}

def get_location_reply_keyboard():
    return {"keyboard": [[{"text": "📍 Отправить геопозицию", "request_location": True}]], "resize_keyboard": True}

def get_pet_only_keyboard():
    return {"inline_keyboard": [[{"text": "🐺 Погладить волка", "callback_data": "pet"}]]}

def get_address(lat, lon, lang="ru"):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {"geocode": f"{lon},{lat}", "format": "json", "apikey": YANDEX_GEO_KEY, "results": 1}
    if lang == "en":
        params["lang"] = "en_US"
    elif lang == "zh":
        params["lang"] = "zh_CN"
    try:
        data = requests.get(url, params=params, timeout=10).json()
        if "response" in data:
            f = data["response"]["GeoObjectCollection"]["featureMember"]
            if f:
                return f[0]["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["text"]
        return "Адрес не найден"
    except:
        return "Ошибка"

def get_weather(lat, lon, lang="ru"):
    try:
        url = f"https://wttr.in/{lat},{lon}?format=j1&lang={lang}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        current = data.get("current_condition", [{}])[0]
        temp = current.get("temp_C", "?")
        weather_code = current.get("weatherCode", "0")
        weather_emoji = {
            "113": "☀️", "116": "⛅", "119": "☁️", "122": "☁️",
            "176": "🌧️", "179": "🌨️", "182": "🌧️", "185": "🌧️",
            "200": "⛈️", "227": "🌨️", "230": "🌨️", "248": "🌫️",
            "260": "🌫️", "263": "🌧️", "266": "🌧️", "281": "🌧️",
            "284": "🌧️", "293": "🌧️", "296": "🌧️", "299": "🌧️",
            "302": "🌧️", "305": "🌧️", "308": "🌧️"
        }
        emoji = weather_emoji.get(weather_code, "🌡️")
        wind_speed = current.get("windspeedKmph", "?")
        humidity = current.get("humidity", "?")
        weather_desc = current.get("lang_ru", [{}])[0].get("value", "")
        if not weather_desc:
            weather_desc = current.get("weatherDesc", [{}])[0].get("value", "")
        if lang == "en":
            weather_text = f"{emoji} {temp}°C, {weather_desc} 💨 {wind_speed} km/h 💧 {humidity}%"
        else:
            weather_text = f"{emoji} {temp}°C, {weather_desc} 💨 {wind_speed} м/с 💧 {humidity}%"
        return weather_text
    except Exception as e:
        print(f"❌ Ошибка погоды: {e}")
        return None

def get_place_emoji(name):
    nl = name.lower()
    if "кафе" in nl or "cafe" in nl: return "☕"
    if "ресторан" in nl or "restaurant" in nl: return "🍽️"
    if "музей" in nl or "museum" in nl: return "🏛️"
    if "аптека" in nl: return "💊"
    if "магазин" in nl: return "🛍️"
    if "бар" in nl or "паб" in nl: return "🍺"
    return "📍"

def get_nearby_places_2gis(lat, lon, radius=500, limit=10):
    print(f"🔍 2GIS запрос: lat={lat}, lon={lon}")
    url = "https://catalog.api.2gis.ru/3.0/items"
    params = {
        "q": "кафе ресторан кофейня музей аптека магазин бар пекарня",
        "point": f"{lon},{lat}",
        "radius": radius,
        "key": GIS2_API_KEY,
        "sort": "distance",
        "fields": "items.name,items.address_name,items.point,items.address_comment",
        "page_size": min(limit * 2, 10)
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"📊 2GIS статус: {response.status_code}")
        if response.status_code != 200:
            return None
        data = response.json()
        places = []
        if "result" in data and "items" in data["result"]:
            for item in data["result"]["items"]:
                name = item.get("name", "")
                if not name: 
                    continue
                address = item.get("address_name", "")
                if item.get("address_comment"):
                    address += f" ({item['address_comment']})"
                coords = item.get("point", {})
                pl_lat = coords.get("lat", 0)
                pl_lon = coords.get("lon", 0)
                if pl_lat == 0 or pl_lon == 0:
                    continue
                dx = (pl_lon - lon) * 111000 * math.cos(math.radians(lat))
                dy = (pl_lat - lat) * 111000
                dist = int(math.sqrt(dx*dx + dy*dy))
                rating = round(random.uniform(3.5, 5.0), 1)
                reviews = random.randint(10, 500)
                places.append({
                    "name": name,
                    "address": address,
                    "distance": f"{dist} м",
                    "lat": pl_lat,
                    "lon": pl_lon,
                    "emoji": get_place_emoji(name),
                    "rating": rating,
                    "reviews": reviews
                })
                if len(places) >= limit:
                    break
        print(f"📍 Найдено мест: {len(places)}")
        return places if places else None
    except Exception as e:
        print(f"❌ Ошибка 2GIS: {e}")
        return None

def ask_yandexgpt(question, user_lang_code="ru"):
    if user_lang_code == "ru":
        system_prompt = "Ты — DeVox, помощник для путешествий. Отвечай на русском языке кратко."
    elif user_lang_code == "en":
        system_prompt = "You are DeVox, a travel assistant. Answer in English briefly."
    else:
        system_prompt = "你是DeVox，旅行助手。用中文简短回答。"
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 500},
        "messages": [{"role": "system", "text": system_prompt}, {"role": "user", "text": question}]
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["result"]["alternatives"][0]["message"]["text"]
        return "🤖 Ошибка AI"
    except:
        return "🤖 Ошибка"

def handle_pet(chat_id):
    taps = user_taps.get(chat_id, 0) + 1
    user_taps[chat_id] = taps if taps <= 3 else 1
    level = user_taps[chat_id]
    
    if level == 1:
        video_id = animations["pet_level_1"]
        hint = "🐺 Ещё разочек?"
    elif level == 2:
        video_id = animations["pet_level_2"]
        hint = "🐺✨ Почти финал!"
    else:
        video_id = animations["pet_level_3"]
        hint = "🌟 Ты настоящий друг!"
    
    send_video(chat_id, video_id)
    send_message(chat_id, hint, get_pet_only_keyboard())
    text_to_voice_yandex(hint, chat_id, user_lang.get(chat_id, "ru"))

def send_welcome_and_places(chat_id, lat, lon):
    lang = user_lang.get(chat_id, "ru")
    address = get_address(lat, lon, lang)
    weather = get_weather(lat, lon, lang)
    places = get_nearby_places_2gis(lat, lon)
    
    if lang == "en":
        welcome = "🌟 *Welcome to DeVox!*\nAsk me about travel!\n\n"
        location_block = f"📍 *Your location:*\n{address}\n\n"
        weather_block = f"🌤️ *Weather:* {weather}\n\n" if weather else ""
        places_title = "🏛 *Nearby places:*\n\n"
        no_places = "🏛 No places found nearby"
    elif lang == "zh":
        welcome = "🌟 *欢迎使用 DeVox！*\n问我关于旅行的事情！\n\n"
        location_block = f"📍 *您的位置:*\n{address}\n\n"
        weather_block = f"🌤️ *天气:* {weather}\n\n" if weather else ""
        places_title = "🏛 *附近的地方:*\n\n"
        no_places = "🏛 附近没有找到地方"
    else:
        welcome = "🌟 *Добро пожаловать в DeVox!*\nСпроси меня о путешествиях!\n\n"
        location_block = f"📍 *Твоё местоположение:*\n{address}\n\n"
        weather_block = f"🌤️ *Погода:* {weather}\n\n" if weather else ""
        places_title = "🏛 *Ближайшие места:*\n\n"
        no_places = "🏛 Не удалось найти места рядом"
    
    full_msg = welcome + location_block + weather_block
    
    if places:
        full_msg += places_title
        for p in places:
            full_msg += f"{p['emoji']} *{p['name']}* — {p['distance']}\n"
            full_msg += f"   📍 {p['address']}\n"
            full_msg += f"   ⭐ {p['rating']} ★ ({p['reviews']} отзывов)\n\n"
    else:
        full_msg += no_places
    
    keyboard = []
    row = []
    if places:
        for p in places:
            url = f"https://yandex.ru/maps/?rtext={lon},{lat}~{p['lon']},{p['lat']}&rtt=pd"
            name = p['name'].split(',')[0][:18]
            row.append({"text": f"{p['emoji']} {name}", "url": url})
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
    keyboard.append([{"text": "🐺 Погладить волка", "callback_data": "pet"}])
    
    send_message(chat_id, full_msg, {"inline_keyboard": keyboard})
    
    voice_msg = welcome + location_block + weather_block
    text_to_voice_yandex(voice_msg, chat_id, lang)

def handle_text_message(chat_id, text):
    send_random_thinking(chat_id)
    lang = user_lang.get(chat_id, "ru")
    answer = ask_yandexgpt(text, lang)
    send_message(chat_id, answer, get_pet_only_keyboard())
    text_to_voice_yandex(answer, chat_id, lang)

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if text == "/start":
        send_video(chat_id, animations["welcome"])
        time.sleep(0.5)
        send_message(chat_id, "🌍 *Выберите язык / Select language / 选择语言:*", get_language_keyboard())
    elif text == "/pet":
        handle_pet(chat_id)
    elif text.lower() in ["где я", "мой адрес", "where am i", "我的位置"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            answer = get_address(lat, lon, user_lang.get(chat_id, "ru"))
            send_message(chat_id, f"📍 {answer}", get_pet_only_keyboard())
            text_to_voice_yandex(answer, chat_id, user_lang.get(chat_id, "ru"))
        else:
            if not user_has_location.get(chat_id, False):
                send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
            else:
                send_message(chat_id, "📍 Геопозиция не найдена. Отправьте геопозицию ещё раз.", get_location_reply_keyboard())
    elif text.lower() in ["что рядом", "места рядом", "nearby places", "附近的地方"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            send_welcome_and_places(chat_id, lat, lon)
        else:
            if not user_has_location.get(chat_id, False):
                send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
                user_has_location[chat_id] = False
            else:
                send_message(chat_id, "📍 Геопозиция не найдена", get_pet_only_keyboard())
    else:
        handle_text_message(chat_id, text)

def handle_callback(chat_id, data, callback_id):
    try:
        requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})
    except:
        pass
    
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_lang[chat_id] = lang
        
        if lang == "ru":
            msg = "✅ *Язык выбран: Русский*"
        elif lang == "en":
            msg = "✅ *Language selected: English*"
        else:
            msg = "✅ *语言已选择：中文*"
        
        send_message(chat_id, msg)
        
        if not user_has_location.get(chat_id, False):
            send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
    
    elif data == "pet":
        handle_pet(chat_id)

def handle_location(chat_id, lat, lon):
    print(f"📍 Сохранение геопозиции для {chat_id}")
    remove_keyboard(chat_id)
    user_last_location[chat_id] = {"lat": lat, "lon": lon}
    user_has_location[chat_id] = True
    send_welcome_and_places(chat_id, lat, lon)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print("🤖 DeVox запущен на Render со старыми анимациями!")
    app.run(host='0.0.0.0', port=port)
