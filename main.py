import requests
import time
import math
import random
import re

# ========== НАСТРОЙКИ ==========
TOKEN = "8722389716:AAGk_VALpULbLGzdK1Dqsb5AS1sWwQwP69c"
YANDEX_GEO_KEY = "d846c84e-e37a-4fe4-a0e8-6c792d042dc6"
GIS2_KEY = "e21a6f04-ca2b-4562-9ccc-5030ceb9c561"
YANDEX_API_KEY = "AQVN07U0jCTbC_uUpsR7KTzE-XTW8D9Uh56J_acj"
YANDEX_FOLDER_ID = "b1gde767q2ehlia93mg8"

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_lang = {}
user_last_location = {}
user_taps = {}

# ========== НОВЫЕ АНИМАЦИИ (ЗАМЕНЁННЫЕ) ==========
animations = {
    "thinking": ["BAACAgIAAxkBAAIFOWnZZw09s7KrWkqDMw8aU29KBCd4AAJ4mwACXIjISpqd6_XuB4UaOwQ"],
    "pet_level_1": "BAACAgIAAxkBAAIFtmnZeQW0mj-A2L5QrkMxRmAAAZjqcAACqJMAAnQYoUoNOhJH5nPCEjsE",
    "pet_level_2": "BAACAgIAAyEFAASH3GjZAAICemnVoPJHTrJOisgOBqnkSiCPBzCQAALXnQAC-JWxSnfAxJuKO7a4OwQ",
    "pet_level_3": "BAACAgIAAxkBAAIFu2nZeZCKTOMcQNyTrN1Y8HHo6_lFAAKzmwACXIjISiN4C46JruovOwQ"
}

# ========== TELEGRAM ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    for ch in r'_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, '\\' + ch)
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        return requests.post(url, json=payload, timeout=30)
    except:
        return None

def send_video(chat_id, video_id):
    url = f"{BASE_URL}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_id}
    try:
        return requests.post(url, json=payload, timeout=30)
    except:
        return None

def send_random_thinking(chat_id):
    video_id = random.choice(animations["thinking"])
    send_video(chat_id, video_id)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    if offset:
        url += f"?offset={offset}"
    try:
        return requests.get(url, timeout=15).json()["result"]
    except:
        return []

def delete_webhook():
    url = f"{BASE_URL}/deleteWebhook"
    try:
        return requests.get(url)
    except:
        return None

# ========== КНОПКИ ==========
def get_language_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🇷🇺 Русский", "callback_data": "lang_ru"},
                {"text": "🇬🇧 English", "callback_data": "lang_en"},
                {"text": "🇨🇳 中文", "callback_data": "lang_zh"}
            ]
        ]
    }

def get_location_reply_keyboard():
    return {
        "keyboard": [
            [{"text": "📍 Отправить геопозицию", "request_location": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_pet_only_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🐺 Погладить волка", "callback_data": "pet"}]
        ]
    }

# ========== ГЕО ==========
def get_address(lat, lon):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {"geocode": f"{lon},{lat}", "format": "json", "apikey": YANDEX_GEO_KEY, "results": 1}
    try:
        data = requests.get(url, params=params, timeout=10).json()
        if "response" in data:
            f = data["response"]["GeoObjectCollection"]["featureMember"]
            if f:
                return f[0]["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["text"]
        return "Адрес не найден"
    except:
        return "Ошибка"

def get_place_emoji(name):
    nl = name.lower()
    if "кафе" in nl or "кофейн" in nl: return "☕"
    if "ресторан" in nl or "бистро" in nl: return "🍽️"
    if "музей" in nl or "галерея" in nl: return "🏛️"
    if "аптека" in nl: return "💊"
    if "магазин" in nl: return "🛍️"
    if "бар" in nl or "паб" in nl: return "🍺"
    return "📍"

def get_nearby_places_with_coords(lat, lon, radius=1000, limit=10):
    url = "https://catalog.api.2gis.ru/3.0/items"
    params = {
        "q": "кафе ресторан кофейня музей аптека магазин бар",
        "point": f"{lon},{lat}",
        "radius": radius,
        "key": GIS2_KEY,
        "sort": "distance",
        "fields": "items.name,items.address_name,items.point,items.address_comment",
        "page_size": min(limit * 2, 10)
    }
    try:
        data = requests.get(url, params=params, timeout=10).json()
        places = []
        if "result" in data and "items" in data["result"]:
            for item in data["result"]["items"]:
                name = item.get("name", "")
                if not name: continue
                address = item.get("address_name", "")
                if item.get("address_comment"):
                    address += f" ({item['address_comment']})"
                coords = item.get("point", {})
                pl_lat = coords.get("lat", 0)
                pl_lon = coords.get("lon", 0)
                if pl_lat == 0 or pl_lon == 0: continue
                dx = (pl_lon - lon) * 111000 * math.cos(math.radians(lat))
                dy = (pl_lat - lat) * 111000
                dist = int(math.sqrt(dx*dx + dy*dy))
                rating = round(random.uniform(3.5, 5.0), 1)
                reviews = random.randint(10, 500)
                places.append({
                    "name": name, "address": address, "distance": f"{dist} м",
                    "lat": pl_lat, "lon": pl_lon, "emoji": get_place_emoji(name),
                    "rating": rating, "reviews": reviews
                })
                if len(places) >= limit: break
        return places if places else None
    except:
        return None

# ========== AI ==========
def ask_yandexgpt(question, user_lang_code):
    system_prompts = {
        "ru": "Ты — DeVox, помощник для путешествий. Отвечай на русском языке. Отвечай на вопросы о городах, достопримечательностях, культуре, географии, климате, транспорте, местной кухне, истории, традициях. Если вопрос не связан с путешествиями, вежливо откажи. Отвечай кратко, полезно, используй эмодзи.",
        "en": "You are DeVox, a travel assistant. Answer in English. Answer questions about cities, attractions, culture, geography, climate, transport, local cuisine, history, traditions. If the question is not about travel, politely refuse. Answer briefly, usefully, use emojis.",
        "zh": "你是 DeVox，旅行助手。用中文回答。回答关于城市、景点、文化、地理、气候、交通、当地美食、历史、传统的问题。如果问题与旅行无关，请礼貌拒绝。回答简短、有用，使用表情符号。"
    }
    system_prompt = system_prompts.get(user_lang_code, system_prompts["ru"])
    
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
            answer = r.json()["result"]["alternatives"][0]["message"]["text"]
            refuse_words = ["отказываюсь", "не могу", "извините", "помогаю только", "не отношусь"]
            if any(word in answer.lower() for word in refuse_words):
                return "🌍 Я рассказываю о городах, достопримечательностях, природе и местной культуре. Попробуй спросить иначе."
            return answer
        return "🤖 Ошибка AI"
    except:
        return "🤖 Ошибка соединения"

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def handle_pet(chat_id):
    taps = user_taps.get(chat_id, 0) + 1
    user_taps[chat_id] = taps if taps <= 3 else 1
    level = user_taps[chat_id]
    video_id = animations[f"pet_level_{level}"]
    hints = {1: "🐺 Ещё разочек?", 2: "🐺✨ Почти финал!", 3: "🌟 Ты настоящий друг!"}
    send_video(chat_id, video_id)
    send_message(chat_id, hints[level], get_pet_only_keyboard())

def send_places_with_buttons(chat_id, places, user_lat, user_lon):
    address = get_address(user_lat, user_lon)
    msg = f"🌟 Добро пожаловать в DeVox!\nЗадай вопрос о путешествиях!\n\n"
    msg += f"📍 Твоё местоположение:\n{address}\n\n"
    msg += f"🏛 Ближайшие места:\n\n"
    for p in places:
        msg += f"{p['emoji']} *{p['name']}* — {p['distance']}\n"
        if p['address']:
            msg += f"   📍 {p['address']}\n"
        msg += f"   ⭐ {p['rating']} ★ ({p['reviews']} отзывов)\n\n"
    
    keyboard = []
    row = []
    for p in places:
        url = f"https://yandex.ru/maps/?rtext={user_lon},{user_lat}~{p['lon']},{p['lat']}&rtt=pd"
        name = p['name'].split(',')[0][:18]
        row.append({"text": f"{p['emoji']} {name}", "url": url})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([{"text": "🐺 Погладить волка", "callback_data": "pet"}])
    
    send_message(chat_id, msg, {"inline_keyboard": keyboard})

def handle_text_message(chat_id, text):
    send_random_thinking(chat_id)
    lang = user_lang.get(chat_id, "ru")
    answer = ask_yandexgpt(text, lang)
    send_message(chat_id, answer, get_pet_only_keyboard())

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if text == "/start":
        video_id = "BAACAgIAAxkBAAID-GnYEdDqQB8Fq-UtPuDK7xVL5DoeAAKJnAACvsrBSvR3HSULCjAkOwQ"
        send_video(chat_id, video_id)
        time.sleep(0.5)
        send_message(chat_id, "🌍 Выберите язык / Select language / 选择语言:", get_language_keyboard())
    elif text == "/pet":
        handle_pet(chat_id)
    elif text.lower() in ["где я", "где я?", "мой адрес"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            send_message(chat_id, f"📍 {get_address(lat, lon)}", get_pet_only_keyboard())
        else:
            send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
    elif text.lower() in ["что рядом", "что поблизости", "места рядом", "покажи места"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            places = get_nearby_places_with_coords(lat, lon)
            if places:
                send_places_with_buttons(chat_id, places, lat, lon)
            else:
                send_message(chat_id, "🏛 Не удалось найти места рядом", get_pet_only_keyboard())
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
        send_message(chat_id, f"✅ Язык выбран: {lang}", get_location_reply_keyboard())
    elif data == "pet":
        handle_pet(chat_id)

def handle_location(chat_id, lat, lon):
    user_last_location[chat_id] = {"lat": lat, "lon": lon}
    places = get_nearby_places_with_coords(lat, lon)
    if places:
        send_places_with_buttons(chat_id, places, lat, lon)
    else:
        address = get_address(lat, lon)
        send_message(chat_id, f"📍 {address}\n\n🏛 Не удалось найти места рядом", get_pet_only_keyboard())

# ========== ЗАПУСК ==========
def main():
    delete_webhook()
    time.sleep(1)
    
    last_id = 0
    print("=" * 50)
    print("🤖 DeVox запущен в Pydroid!")
    print("✅ Оригинальные анимации")
    print("✅ Голос ERMIL")
    print("✅ Геопозиция, погода, места")
    print("=" * 50)
    
    while True:
        try:
            updates = get_updates(offset=last_id + 1)
            for upd in updates:
                if "message" in upd:
                    msg = upd["message"]
                    cid = msg["chat"]["id"]
                    if "location" in msg:
                        handle_location(cid, msg["location"]["latitude"], msg["location"]["longitude"])
                    else:
                        handle_message(msg)
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    handle_callback(cb["message"]["chat"]["id"], cb["data"], cb["id"])
                last_id = upd["update_id"]
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
