import requests
import time
import math
import random
import re
import os
from flask import Flask, request, jsonify

# ========== ПЕРЕМЕННЫЕ ИЗ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN")
YANDEX_GEO_KEY = os.environ.get("YANDEX_GEO_KEY")
GIS2_API_KEY = os.environ.get("GIS2_API_KEY")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")

# Проверяем, что все переменные загружены
if not all([TOKEN, YANDEX_GEO_KEY, GIS2_API_KEY, YANDEX_API_KEY, YANDEX_FOLDER_ID]):
    print("❌ ОШИБКА: Не все переменные окружения установлены!")
    print("Нужны: BOT_TOKEN, YANDEX_GEO_KEY, GIS2_API_KEY, YANDEX_API_KEY, YANDEX_FOLDER_ID")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_lang = {}
user_last_location = {}
user_taps = {}

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
        
        print(f"📩 Получено обновление")
        
        if "message" in update:
            handle_message(update["message"])
        elif "callback_query" in update:
            cb = update["callback_query"]
            handle_callback(cb["message"]["chat"]["id"], cb["data"], cb["id"])
        
        return "ok", 200
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return "error", 500

# ========== TELEGRAM ФУНКЦИИ ==========
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
        return response
    except Exception as e:
        print(f"❌ Ошибка send_message: {e}")
        return None

def send_video(chat_id, video_id):
    url = f"{BASE_URL}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_id}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print(f"✅ Видео отправлено")
        return response
    except Exception as e:
        print(f"❌ Ошибка send_video: {e}")
        return None

def send_random_thinking(chat_id):
    video_id = random.choice(animations["thinking"])
    return send_video(chat_id, video_id)

# ========== АНИМАЦИИ ==========
animations = {
    "thinking": ["BAACAgIAAxkBAAIFOWnZZw09s7KrWkqDMw8aU29KBCd4AAJ4mwACXIjISpqd6_XuB4UaOwQ"],
    "pet_level_1": "BAACAgIAAxkBAAIFtmnZeQW0mj-A2L5QrkMxRmAAAZjqcAACqJMAAnQYoUoNOhJH5nPCEjsE",
    "pet_level_2": "BAACAgIAAyEFAASH3GjZAAICemnVoPJHTrJOisgOBqnkSiCPBzCQAALXnQAC-JWxSnfAxJuKO7a4OwQ",
    "pet_level_3": "BAACAgIAAxkBAAIFu2nZeZCKTOMcQNyTrN1Y8HHo6_lFAAKzmwACXIjISiN4C46JruovOwQ"
}

# ========== TTS (ГОЛОС) ==========
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
        print(f"🎙️ Озвучиваю: {clean_text[:50]}...")
        response = requests.post(url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            files = {"voice": ("voice.ogg", response.content, "audio/ogg")}
            send_result = requests.post(
                f"{BASE_URL}/sendVoice",
                data={"chat_id": chat_id},
                files=files,
                timeout=30
            )
            if send_result.status_code == 200:
                print("✅ Голос отправлен!")
                return True
        else:
            print(f"❌ TTS ошибка: {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ TTS исключение: {e}")
        return False

# ========== КНОПКИ ==========
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

# ========== ГЕО (2GIS) ==========
def get_address(lat, lon, lang="ru"):
    """Получение адреса через Яндекс.Геокодер"""
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "geocode": f"{lon},{lat}",
        "format": "json",
        "apikey": YANDEX_GEO_KEY,
        "results": 1
    }
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
        return "Address not found" if lang == "en" else "Адрес не найден" if lang == "ru" else "地址未找到"
    except Exception as e:
        print(f"❌ Ошибка геокодера: {e}")
        return "Error" if lang == "en" else "Ошибка" if lang == "ru" else "错误"

def get_place_emoji(name):
    nl = name.lower()
    if "кафе" in nl or "coffee" in nl or "cafe" in nl: return "☕"
    if "ресторан" in nl or "restaurant" in nl: return "🍽️"
    if "музей" in nl or "museum" in nl: return "🏛️"
    if "аптека" in nl or "pharmacy" in nl: return "💊"
    if "магазин" in nl or "shop" in nl: return "🛍️"
    if "бар" in nl or "bar" in nl or "паб" in nl: return "🍺"
    if "пекарн" in nl or "bakery" in nl: return "🥖"
    return "📍"

def get_nearby_places_2gis(lat, lon, radius=500, limit=10):
    """Поиск мест через 2GIS API"""
    print(f"🔍 2GIS запрос: lat={lat}, lon={lon}")
    
    url = "https://catalog.api.2gis.ru/3.0/items"
    params = {
        "q": "кафе ресторан кофейня музей аптека магазин бар пекарня",
        "point": f"{lon},{lat}",
        "radius": radius,
        "key": GIS2_API_KEY,
        "sort": "distance",
        "page_size": min(limit * 2, 10)
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"📊 2GIS статус: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Ошибка 2GIS: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return None
        
        data = response.json()
        places = []
        
        if "result" in data and "items" in data["result"]:
            print(f"📊 2GIS нашёл {len(data['result']['items'])} мест")
            
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
                
                # Расчёт расстояния
                dx = (pl_lon - lon) * 111000 * math.cos(math.radians(lat))
                dy = (pl_lat - lat) * 111000
                dist = int(math.sqrt(dx*dx + dy*dy))
                
                # Демо-рейтинг
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
        
        print(f"📍 Обработано мест: {len(places)}")
        return places if places else None
        
    except Exception as e:
        print(f"❌ Ошибка 2GIS: {e}")
        return None

# ========== AI (YandexGPT) ==========
def ask_yandexgpt(question, user_lang_code="ru"):
    if user_lang_code == "ru":
        system_prompt = """Ты — DeVox, помощник для путешествий. Отвечай на русском языке. Отвечай о городах, достопримечательностях, культуре, географии, климате, транспорте, кухне, истории, традициях. Отвечай кратко, используй эмодзи."""
    elif user_lang_code == "en":
        system_prompt = """You are DeVox, a travel assistant. Answer in English. Answer about cities, attractions, culture, geography, climate, transport, cuisine, history, traditions. Answer briefly, use emojis."""
    else:
        system_prompt = """你是DeVox，旅行助手。用中文回答。回答关于城市、景点、文化、地理、气候、交通、美食、历史、传统的问题。回答简短，使用表情符号。"""
    
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
    except Exception as e:
        print(f"❌ AI ошибка: {e}")
        return "🤖 Ошибка"

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def handle_pet(chat_id):
    taps = user_taps.get(chat_id, 0) + 1
    user_taps[chat_id] = taps if taps <= 3 else 1
    level = user_taps[chat_id]
    video_id = animations[f"pet_level_{level}"]
    hints = {1: "🐺 Ещё разочек?", 2: "🐺✨ Почти финал!", 3: "🌟 Ты настоящий друг!"}
    send_video(chat_id, video_id)
    send_message(chat_id, hints[level], get_pet_only_keyboard())
    text_to_voice_yandex(hints[level], chat_id, user_lang.get(chat_id, "ru"))

def send_welcome_and_places(chat_id, lat, lon):
    """Отправляет приветствие и список мест после получения геолокации"""
    print(f"📍 send_welcome_and_places вызвана для чата {chat_id}")
    print(f"📍 Координаты: lat={lat}, lon={lon}")
    
    lang = user_lang.get(chat_id, "ru")
    address = get_address(lat, lon, lang)
    print(f"📍 Адрес: {address}")
    
    places = get_nearby_places_2gis(lat, lon)
    print(f"📍 Найдено мест: {len(places) if places else 0}")
    
    if places:
        for p in places[:3]:
            print(f"   - {p['name']} ({p['distance']})")
    
    if lang == "en":
        welcome = "🌟 *Welcome to DeVox!*\nAsk me about travel!\n\n"
        location_block = f"📍 *Your location:*\n{address}\n\n"
        places_title = "🏛 *Nearby places:*\n\n"
        no_places = "🏛 No places found nearby"
    elif lang == "zh":
        welcome = "🌟 *欢迎使用 DeVox！*\n问我关于旅行的事情！\n\n"
        location_block = f"📍 *您的位置:*\n{address}\n\n"
        places_title = "🏛 *附近的地方:*\n\n"
        no_places = "🏛 附近没有找到地方"
    else:
        welcome = "🌟 *Добро пожаловать в DeVox!*\nСпроси меня о путешествиях!\n\n"
        location_block = f"📍 *Твоё местоположение:*\n{address}\n\n"
        places_title = "🏛 *Ближайшие места:*\n\n"
        no_places = "🏛 Не удалось найти места рядом"
    
    if places:
        places_block = places_title
        for p in places:
            places_block += f"{p['emoji']} *{p['name']}* — {p['distance']}\n"
            places_block += f"   📍 {p['address']}\n"
            places_block += f"   ⭐ {p['rating']} ★ ({p['reviews']} отзывов)\n\n"
    else:
        places_block = no_places
    
    full_msg = welcome + location_block + places_block
    print(f"📝 Длина сообщения: {len(full_msg)} символов")
    
    # Кнопки маршрутов
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
        send_video(chat_id, "BAACAgIAAxkBAAID-GnYEdDqQB8Fq-UtPuDK7xVL5DoeAAKJnAACvsrBSvR3HSULCjAkOwQ")
        time.sleep(0.5)
        send_message(chat_id, "🌍 *Выберите язык:*", get_language_keyboard())
    elif text == "/pet":
        handle_pet(chat_id)
    elif text.lower() in ["где я", "мой адрес", "where am i", "我的位置"]:
        lang = user_lang.get(chat_id, "ru")
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            answer = get_address(lat, lon, lang)
            prefix = "📍 Your location:\n" if lang == "en" else "📍 Твоё местоположение:\n"
            send_message(chat_id, f"{prefix}{answer}", get_pet_only_keyboard())
            text_to_voice_yandex(answer, chat_id, lang)
        else:
            send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
    elif text.lower() in ["что рядом", "места рядом", "nearby places", "附近的地方"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            send_welcome_and_places(chat_id, lat, lon)
        else:
            send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
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
            msg = "✅ *Язык выбран: Русский*\n\n📍 Отправь геопозицию"
        elif lang == "en":
            msg = "✅ *Language selected: English*\n\n📍 Send your location"
        else:
            msg = "✅ *语言已选择：中文*\n\n📍 发送您的位置"
        
        send_message(chat_id, msg, get_location_reply_keyboard())
    elif data == "pet":
        handle_pet(chat_id)

def handle_location(chat_id, lat, lon):
    user_last_location[chat_id] = {"lat": lat, "lon": lon}
    send_welcome_and_places(chat_id, lat, lon)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    
    print("=" * 50)
    print("🤖 DeVox запущен на Render (Webhook + 2GIS)!")
    print(f"✅ Порт: {port}")
    print("✅ Голос ERMIL для всех языков")
    print("✅ 2GIS ключ загружен")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port)
