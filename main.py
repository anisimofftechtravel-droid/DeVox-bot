import requests
import time
import math
import random
import re
from datetime import datetime, timedelta
from flask import Flask, request
import os

TOKEN = os.environ.get("BOT_TOKEN")
YANDEX_GEO_KEY = os.environ.get("YANDEX_GEO_KEY")
GIS2_KEY = os.environ.get("GIS2_API_KEY")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_lang = {}
user_last_location = {}
user_taps = {}
user_has_location = {}

ANIMATIONS = {
    "welcome_start": "BAACAgIAAxkBAAILQ2nirvnxUjPXpIX1Ur1oqliyei1iAAJOoQAC3uwZS0PtHYa-KQqAOwQ",
    "welcome_location": "BAACAgIAAxkBAAILRWnir2DvrKYj0boh4WSuAmhXmUHvAAJQoQAC3uwZS5SwdiiC9o1mOwQ",
    "thinking": "BAACAgIAAxkBAAILR2nir6Ngb09yzNJcgqVQ0ewOh9vNAAJWoQAC3uwZS8MQQItC-5OvOwQ",
    "pet_level_1": "BAACAgIAAxkBAAILSWnir-vZm75XH9IhHBJ-3zQXID-yAAJXoQAC3uwZSx8YulmJTROmOwQ",
    "pet_level_2": "BAACAgIAAxkBAAILS2nisCh8PgEvJ-unnvK3NkOnhFTzAAJYoQAC3uwZS1UbOuDRX-CxOwQ",
    "pet_level_3": "BAACAgIAAxkBAAILTWnisFsiUkp-XGLS-G8FdNJkCOVsAAJcoQAC3uwZS_ihaLZLr0cpOwQ"
}

app = Flask(__name__)

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
    except:
        return None

def send_video(chat_id, video_id):
    url = f"{BASE_URL}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_id}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("✅ Видео отправлено")
        return response
    except:
        return None

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

def get_weather_by_city(city_name, day_offset=0, lang="ru"):
    try:
        url = f"https://wttr.in/{city_name}?format=j1&lang={lang}&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if day_offset == 0:
            current = data.get("current_condition", [{}])[0]
            temp = current.get("temp_C", "?")
            weather_desc = current.get("lang_ru", [{}])[0].get("value", "")
            if not weather_desc or "?" in weather_desc:
                weather_desc = current.get("weatherDesc", [{}])[0].get("value", "")
            if not weather_desc:
                weather_desc = "данные не получены"
            weather_desc = re.sub(r'[^\w\sа-яА-Яa-zA-Z\- ]', '', weather_desc)
            wind_speed = current.get("windspeedKmph", "?")
            humidity = current.get("humidity", "?")
            weather_code = current.get("weatherCode", "0")
        else:
            weather_data = data.get("weather", [])
            if day_offset - 1 < len(weather_data):
                day_data = weather_data[day_offset - 1]
                hourly = day_data.get("hourly", [])
                if hourly:
                    mid_hour = hourly[len(hourly)//2] if hourly else hourly[0]
                    temp = mid_hour.get("tempC", "?")
                    weather_desc = mid_hour.get("lang_ru", [{}])[0].get("value", "")
                    if not weather_desc:
                        weather_desc = mid_hour.get("weatherDesc", [{}])[0].get("value", "")
                    weather_desc = re.sub(r'[^\w\sа-яА-Яa-zA-Z\- ]', '', weather_desc)
                    wind_speed = mid_hour.get("windspeedKmph", "?")
                    humidity = mid_hour.get("humidity", "?")
                    weather_code = mid_hour.get("weatherCode", "0")
                else:
                    return None
            else:
                return None
        
        weather_emoji = {
            "113": "☀️", "116": "⛅", "119": "☁️", "122": "☁️",
            "176": "🌧️", "179": "🌨️", "182": "🌧️", "185": "🌧️",
            "200": "⛈️", "227": "🌨️", "230": "🌨️", "248": "🌫️",
            "260": "🌫️", "263": "🌧️", "266": "🌧️", "281": "🌧️",
            "284": "🌧️", "293": "🌧️", "296": "🌧️", "299": "🌧️",
            "302": "🌧️", "305": "🌧️", "308": "🌧️", "311": "🌧️",
            "314": "🌧️", "317": "🌧️", "320": "🌨️", "323": "🌨️",
            "326": "🌨️", "329": "🌨️", "332": "🌨️", "335": "🌨️",
            "338": "🌨️", "350": "🌧️", "353": "🌧️", "356": "🌧️",
            "359": "🌧️", "362": "🌧️", "365": "🌧️", "368": "🌨️",
            "371": "🌨️", "374": "🌨️", "377": "🌨️", "386": "⛈️",
            "389": "⛈️", "392": "⛈️", "395": "🌨️"
        }
        emoji = weather_emoji.get(weather_code, "🌡️")
        
        return {
            "temp": temp,
            "condition": weather_desc,
            "emoji": emoji,
            "wind": wind_speed,
            "humidity": humidity
        }
    except Exception as e:
        print(f"❌ Ошибка погоды: {e}")
        return None

def is_travel_related(question):
    question_lower = question.lower()
    
    # Вопросы о самом боте
    devox_keywords = ["devox", "девокс", "кто ты", "что ты", "твоя задача", "помощник", "бот"]
    for keyword in devox_keywords:
        if keyword in question_lower:
            return True
    
    # Еда и бронирование
    food_booking_keywords = [
        "поесть", "еда", "ресторан", "кафе", "кофейня", "бистро", "столовая",
        "завтрак", "обед", "ужин", "перекус", "попробовать", "блюдо", "кухня",
        "забронировать", "бронь", "столик", "заказать", "доставка", "что поесть",
        "где поесть", "вкусно", "покушать"
    ]
    for keyword in food_booking_keywords:
        if keyword in question_lower:
            return True
    
    # Основные туристические темы
    travel_keywords = [
        "путешеств", "тур", "поездк", "город", "города", "городе", "столица", "страна", 
        "достопримечательност", "кремль", "собор", "музей", "парк", "пляж", "море", "горы",
        "отель", "гостиниц", "билет", "самолет", "поезд", "автобус", "экскурс",
        "погода", "климат", "авиа", "жд", "концерт", "выставк", "фестивал", "театр", "кинотеатр",
        "маршрут", "карт", "навигац", "виза", "паспорт", "валюта", "трансфер", "аэропорт",
        "вокзал", "метро", "такси", "аренда", "экскурсия", "гид", "сувенир", "шопинг", "рынок",
        "памятник", "церковь", "замок", "крепость", "природ", "озеро", "водопад",
        "где я", "мой адрес", "что рядом", "места рядом", "погладить волка", "pet",
        "расскажи про", "расскажи о", "что посмотреть", "что интересного",
        "добраться", "как добраться", "дорога", "маршрут", "транспорт"
    ]
    for keyword in travel_keywords:
        if keyword in question_lower:
            return True
    
    # Города
    cities = ["москва", "питер", "спб", "сочи", "казань", "стамбул", "париж", "лондон", "берлин", 
              "рим", "токио", "пекин", "прага", "варшава", "нью-йорк", "набережные челны", "челны"]
    for city in cities:
        if city in question_lower:
            return True
    
    return False

def ask_yandexgpt(question, user_lang_code="ru"):
    if not is_travel_related(question):
        if user_lang_code == "ru":
            return "🌍 *Извините, я отвечаю только на вопросы о путешествиях, туризме, городах, достопримечательностях, погоде, билетах, отелях, транспорте и мероприятиях.*\n\nЗадайте вопрос, связанный с путешествиями, например:\n• Расскажи о Париже\n• Что посмотреть в Стамбуле?\n• Какая погода в Сочи?\n• Найди билеты в Москву\n• Как добраться из Москвы в Казань?\n• Что происходит в Санкт-Петербурге?\n• Где я?\n• Что рядом?\n• Кто ты? (вопрос обо мне)"
        elif user_lang_code == "en":
            return "🌍 *Sorry, I only answer questions about travel, tourism, cities, attractions, weather, tickets, hotels, transport and events.*\n\nAsk a travel-related question, for example:\n• Tell me about Paris\n• What to see in Istanbul?\n• What's the weather in Sochi?\n• Find tickets to Moscow\n• How to get from Moscow to Kazan?\n• Where am I?\n• What's nearby?\n• Who are you? (questions about me)"
        else:
            return "🌍 *抱歉，我只回答关于旅行、旅游、城市、景点、天气、机票、酒店、交通和活动的问题。*\n\n请提出与旅行相关的问题，例如：\n• 告诉我关于巴黎的事\n• 在伊斯坦布尔看什么？\n• 索契的天气怎么样？\n• 查找去莫斯科的机票\n• 如何从莫斯科到喀山？\n• 我在哪里？\n• 附近有什么？\n• 你是谁？（关于我的问题）"
    
    if user_lang_code == "ru":
        system_prompt = "Ты — DeVox, помощник для путешествий с головой волка. Отвечай на русском языке кратко, используй эмодзи. Отвечай на вопросы о путешествиях, городах, достопримечательностях, культуре, географии, климате, транспорте, как добраться, билетах, отелях, погоде, мероприятиях, а также о еде и ресторанах. Если спрашивают о тебе — расскажи, что ты DeVox, голосовой помощник для путешествий. Твой характер — дружелюбный волк."
    elif user_lang_code == "en":
        system_prompt = "You are DeVox, a travel assistant with a wolf head. Answer in English briefly, use emojis. Answer questions about travel, cities, attractions, culture, geography, climate, transport, how to get, tickets, hotels, weather, events, and also about food and restaurants. If asked about yourself, tell that you are DeVox, a voice travel assistant. Your character is a friendly wolf."
    else:
        system_prompt = "你是DeVox，一个长着狼头的旅行助手。用中文简短回答，使用表情符号。回答关于旅行、城市、景点、文化、地理、气候、交通、如何到达、机票、酒店、天气、活动的问题，也包括关于食物和餐厅的问题。如果问起你自己，告诉他们你是DeVox，一个语音旅行助手。你的性格是友好的狼。"
    
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
        return f"🤖 Ошибка AI"
    except:
        return f"🤖 Ошибка"

def get_place_recommendation(place_name, lang="ru"):
    """Генерирует короткую рекомендацию для места через YandexGPT"""
    if lang == "ru":
        prompt = f"Напиши очень короткую рекомендацию для туриста о месте '{place_name}'. Одно предложение, с эмодзи, без лишних слов. Например: '☕ Здесь варят лучший кофе в городе' или '🥐 Их плюшки тают во рту'."
    elif lang == "en":
        prompt = f"Write a very short recommendation for a tourist about '{place_name}'. One sentence with emoji. Example: '☕ They brew the best coffee in town' or '🥐 Their pastries melt in your mouth'."
    else:
        prompt = f"为游客写一条关于'{place_name}'的简短推荐。一句话，带表情符号。例如：'☕ 这里有全城最好的咖啡'或'🥐 他们的面包入口即化'。"
    
    answer = ask_yandexgpt(prompt, lang)
    if not answer or len(answer) > 150 or "Ошибка" in answer:
        if lang == "ru":
            return "📍 Место заслуживает внимания!"
        else:
            return "📍 This place is worth checking out!"
    return answer

def get_weather_with_facts(city_name, day_offset=0, lang="ru"):
    weather = get_weather_by_city(city_name, day_offset, lang)
    
    if not weather:
        if lang == "ru":
            return f"🌍 *{city_name.capitalize()}*\n\n❌ Не удалось получить данные о погоде. Проверьте название города.\n\n🗺️ Например: Москва, Санкт-Петербург, Сочи, Стамбул, Париж", None, None, None
        else:
            return f"🌍 *{city_name.capitalize()}*\n\n❌ Could not get weather data. Check the city name.", None, None, None
    
    fact_prompt = f"Расскажи один короткий интересный факт о городе {city_name}. Только факт, без лишних слов, 1-2 предложения. Используй эмодзи."
    fact = ask_yandexgpt(fact_prompt, lang)
    
    if not fact or "Ошибка" in fact:
        if lang == "ru":
            fact = "🏛️ Интересных фактов пока нет, но город определённо стоит посетить!"
        else:
            fact = "🏛️ No interesting facts at the moment, but the city is definitely worth visiting!"
    
    day_names = ["сегодня", "завтра", "послезавтра"]
    day_text = day_names[day_offset] if day_offset < len(day_names) else f"через {day_offset} дней"
    
    if lang == "ru":
        response = f"🌍 *{city_name.capitalize()}*\n\n"
        response += f"{weather['emoji']} *{day_text.capitalize()}* **+{weather['temp']}°C**, {weather['condition'].lower()}, "
        response += f"ветер {weather['wind']} м/с, влажность {weather['humidity']}%.\n\n"
        response += f"🏝️ *Интересный факт:* {fact}\n\n"
        response += "🗺️ Хотите узнать о других городах? Спросите меня!"
    else:
        response = f"🌍 *{city_name.capitalize()}*\n\n"
        response += f"{weather['emoji']} *{day_text.capitalize()}* **+{weather['temp']}°C**, {weather['condition'].lower()}, "
        response += f"wind {weather['wind']} m/s, humidity {weather['humidity']}%.\n\n"
        response += f"🏝️ *Interesting fact:* {fact}\n\n"
        response += "🗺️ Want to know about other cities? Ask me!"
    
    return response, weather, fact, day_text

def get_weather_for_voice_by_city(weather, fact, day_text, lang="ru"):
    temp = weather.get("temp", "?")
    weather_desc = weather.get("condition", "").lower()
    wind_speed = int(weather.get("wind", "0"))
    humidity = weather.get("humidity", "?")
    
    if wind_speed == 0:
        wind_text = "безветренно"
    elif wind_speed <= 2:
        wind_text = "лёгкий ветер"
    elif wind_speed <= 5:
        wind_text = "слабый ветер"
    elif wind_speed <= 10:
        wind_text = "умеренный ветер"
    else:
        wind_text = f"ветер {wind_speed} метров в секунду"
    
    humidity_text = f"влажность {humidity} процентов"
    
    if lang == "ru":
        return f"{day_text}, {temp} градусов, {weather_desc}. {wind_text}. {humidity_text}. {fact}. Хотите узнать о других городах? Спросите меня!"
    else:
        return f"{day_text}, {temp} degrees, {weather_desc}. {wind_text}. {humidity_text}. {fact}. Want to know about other cities? Ask me!"

def extract_city_and_day_from_text(text):
    text_lower = text.lower()
    
    day_offset = 0
    if "завтра" in text_lower:
        day_offset = 1
    elif "послезавтра" in text_lower:
        day_offset = 2
    elif "неделя" in text_lower or "через неделю" in text_lower:
        day_offset = 7
    elif "через" in text_lower:
        match = re.search(r'через\s+(\d+)\s+дней?', text_lower)
        if match:
            day_offset = int(match.group(1))
    
    clean_text = text_lower
    for word in ["завтра", "послезавтра", "через неделю", "неделю", "через"]:
        clean_text = clean_text.replace(word, "")
    
    special_cases = {
        "набережные челны": ["набережные челны", "набережных челнах", "набережные челнах", "челны", "нч"],
        "санкт-петербург": ["санкт-петербург", "питер", "петербург", "спб"],
        "нижний новгород": ["нижний новгород", "нижнем новгороде", "нижний"],
        "ростов-на-дону": ["ростов-на-дону", "ростове-на-дону"],
        "москва": ["москва", "москвы", "москве", "москву", "москвой", "мск"],
        "сочи": ["сочи"],
        "казань": ["казань", "казани", "казанью", "казан"],
        "екатеринбург": ["екатеринбург", "екатеринбурге", "екб"],
        "новосибирск": ["новосибирск", "новосибирске"],
        "владивосток": ["владивосток", "владивостоке"],
        "калининград": ["калининград", "калининграде"],
        "стамбул": ["стамбул", "стамбуле", "стамбула"],
        "париж": ["париж", "париже", "парижа"],
        "лондон": ["лондон", "лондоне", "лондона"],
        "нью-йорк": ["нью-йорк", "нью-йорке", "нью-йорка", "нью йорк"],
        "берлин": ["берлин", "берлине", "берлина"],
        "рим": ["рим", "риме", "рима"],
        "токио": ["токио"],
        "пекин": ["пекин", "пекине", "пекина"],
        "прага": ["прага", "праге", "прагу"],
        "варшава": ["варшава", "варшаве", "варшаву"],
    }
    
    for city, variants in special_cases.items():
        for variant in variants:
            if variant in clean_text:
                return city, day_offset
    
    words_to_remove = ["какая", "погода", "во", "на", "сегодня", "сейчас", "температура", "weather", "в", "какой", "будет", "как", "добраться", "быстро"]
    query = clean_text
    for word in words_to_remove:
        query = query.replace(word, "")
    query = query.strip()
    
    if len(query) > 2 and query not in ["", " "]:
        return query, day_offset
    
    return None, day_offset

def get_weather(lat, lon, lang="ru"):
    try:
        url = f"https://wttr.in/{lat},{lon}?format=j1&lang={lang}&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
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
        weather_desc = re.sub(r'[^\w\sа-яА-Яa-zA-Z\- ]', '', weather_desc)
        if lang == "en":
            weather_text = f"{emoji} {temp}°C, {weather_desc} 💨 {wind_speed} km/h 💧 {humidity}%"
        else:
            weather_text = f"{emoji} {temp}°C, {weather_desc} 💨 {wind_speed} м/с 💧 {humidity}%"
        return weather_text
    except:
        return None

def get_weather_for_voice(lat, lon, lang="ru"):
    try:
        url = f"https://wttr.in/{lat},{lon}?format=j1&lang={lang}&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return None
        data = response.json()
        current = data.get("current_condition", [{}])[0]
        temp = current.get("temp_C", "?")
        weather_desc = current.get("lang_ru", [{}])[0].get("value", "")
        if not weather_desc:
            weather_desc = current.get("weatherDesc", [{}])[0].get("value", "")
        weather_desc = re.sub(r'[^\w\sа-яА-Яa-zA-Z\- ]', '', weather_desc).lower()
        wind_speed = int(current.get("windspeedKmph", "0"))
        
        if wind_speed == 0:
            wind_text = "безветренно"
        elif wind_speed <= 2:
            wind_text = "лёгкий ветер"
        elif wind_speed <= 5:
            wind_text = "слабый ветер"
        elif wind_speed <= 10:
            wind_text = "умеренный ветер"
        else:
            wind_text = f"ветер {wind_speed} метров в секунду"
        
        return f"сегодня, {temp} градусов, {weather_desc}. {wind_text}."
    except Exception as e:
        print(f"❌ Ошибка get_weather_for_voice: {e}")
        return None

def get_place_emoji(name):
    nl = name.lower()
    if "кафе" in nl or "кофейн" in nl: return "☕"
    if "ресторан" in nl or "бистро" in nl: return "🍽️"
    if "музей" in nl or "галерея" in nl: return "🏛️"
    if "аптека" in nl: return "💊"
    if "магазин" in nl: return "🛍️"
    if "бар" in nl or "паб" in nl: return "🍺"
    return "📍"

def get_nearby_places_2gis(lat, lon, radius=500, limit=5):
    url = "https://catalog.api.2gis.ru/3.0/items"
    params = {
        "q": "кафе ресторан кофейня музей аптека магазин бар",
        "point": f"{lon},{lat}",
        "radius": radius,
        "key": GIS2_KEY,
        "sort": "distance",
        "fields": "items.name,items.address_name,items.point",
        "page_size": limit
    }
    try:
        data = requests.get(url, params=params, timeout=10).json()
        places = []
        if "result" in data and "items" in data["result"]:
            for item in data["result"]["items"]:
                name = item.get("name", "")
                if not name: continue
                address = item.get("address_name", "")
                coords = item.get("point", {})
                pl_lat = coords.get("lat", 0)
                pl_lon = coords.get("lon", 0)
                if pl_lat == 0: continue
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

def handle_pet(chat_id):
    taps = user_taps.get(chat_id, 0) + 1
    user_taps[chat_id] = taps if taps <= 3 else 1
    level = user_taps[chat_id]
    videos = {1: ANIMATIONS["pet_level_1"], 2: ANIMATIONS["pet_level_2"], 3: ANIMATIONS["pet_level_3"]}
    hints = {1: "🐺 Ещё разочек?", 2: "🐺✨ Почти финал!", 3: "🌟 Ты настоящий друг!"}
    send_video(chat_id, videos[level])
    send_message(chat_id, hints[level], get_pet_only_keyboard())
    text_to_voice_yandex(hints[level], chat_id)

def send_welcome_and_places(chat_id, lat, lon, custom_message=None):
    send_video(chat_id, ANIMATIONS["welcome_location"])
    time.sleep(0.5)
    lang = user_lang.get(chat_id, "ru")
    address = get_address(lat, lon, lang)
    weather_display = get_weather(lat, lon, lang)
    weather_voice = get_weather_for_voice(lat, lon, lang)
    places = get_nearby_places_2gis(lat, lon, radius=500, limit=5)
    
    if custom_message:
        msg = f"🌟 {custom_message}\n\n"
    else:
        msg = f"🌟 *Добро пожаловать в DeVox!*\n\n"
    
    msg += f"📍 *Твоё местоположение:*\n{address}\n\n"
    if weather_display:
        msg += f"🌤️ *Погода:* {weather_display}\n\n"
    
    if places:
        msg += f"🍽️ *Где поесть рядом:*\n\n"
        keyboard = []
        for p in places:
            recommendation = get_place_recommendation(p['name'], lang)
            msg += f"{p['emoji']} *{p['name']}* — {p['distance']}\n"
            msg += f"   📍 {p['address']}\n"
            msg += f"   💡 {recommendation}\n"
            msg += f"   ⭐ {p['rating']} ★ ({p['reviews']} отзывов)\n\n"
            
            route_url = f"https://yandex.ru/maps/?rtext={lon},{lat}~{p['lon']},{p['lat']}&rtt=pd"
            name_short = p['name'].split(',')[0][:18]
            keyboard.append([{"text": f"🧭 {name_short}", "url": route_url}])
            keyboard.append([{"text": f"📞 Забронировать {name_short}", "callback_data": f"booking_{p['name'][:20]}"}])
        
        keyboard.append([{"text": "🐺 Погладить волка", "callback_data": "pet"}])
        send_message(chat_id, msg, {"inline_keyboard": keyboard})
    else:
        msg += f"🍽️ *Где поесть рядом:*\nНе найдены\n\n"
        send_message(chat_id, msg, get_pet_only_keyboard())
    
    voice_msg = f"Добро пожаловать в DeVox. Твоё местоположение: {address}. "
    if weather_voice:
        voice_msg += f"Погода: {weather_voice}"
    else:
        voice_msg += "Погода: данные не получены."
    text_to_voice_yandex(voice_msg, chat_id, lang)

def handle_text_message(chat_id, text):
    send_video(chat_id, ANIMATIONS["thinking"])
    lang = user_lang.get(chat_id, "ru")
    
    food_keywords = ["поесть", "еда", "ресторан", "кафе", "кофейня", "где поесть", "что поесть", "покушать", "вкусно", "завтракать", "обедать", "ужинать"]
    is_food_question = any(word in text.lower() for word in food_keywords)
    
    if is_food_question and chat_id in user_last_location:
        lat = user_last_location[chat_id]["lat"]
        lon = user_last_location[chat_id]["lon"]
        send_welcome_and_places(chat_id, lat, lon, custom_message="🍽️ *Вот что я нашёл для тебя:*")
        return
    
    if is_food_question:
        send_message(chat_id, "📍 *Чтобы я нашёл места, где можно поесть, отправь мне свою геопозицию.*\n\nНажми на кнопку ниже, чтобы поделиться местоположением.", get_location_reply_keyboard())
        return
    
    city, day_offset = extract_city_and_day_from_text(text)
    weather_keywords = ["погод", "weather", "температур", "temp", "градус", "солнеч", "дожд", "ветер", "облач", "пасмур", "ясно", "мороз", "тепл", "холод", "завтра", "сегодня", "сейчас", "неделя"]
    is_weather = any(word in text.lower() for word in weather_keywords)
    
    if city and is_weather:
        answer, weather, fact, day_text = get_weather_with_facts(city, day_offset, lang)
        send_message(chat_id, answer, get_pet_only_keyboard())
        if weather and fact:
            voice_full = get_weather_for_voice_by_city(weather, fact, day_text, lang)
            text_to_voice_yandex(voice_full, chat_id, lang)
        else:
            text_to_voice_yandex(answer, chat_id, lang)
    else:
        answer = ask_yandexgpt(text, lang)
        send_message(chat_id, answer, get_pet_only_keyboard())
        text_to_voice_yandex(answer, chat_id, lang)

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    if text == "/start":
        send_video(chat_id, ANIMATIONS["welcome_start"])
        time.sleep(0.5)
        send_message(chat_id, "🌍 *Выберите язык / Select language / 选择语言:*", get_language_keyboard())
    elif text == "/pet":
        handle_pet(chat_id)
    elif text.lower() in ["где я", "мой адрес", "where am i", "我的位置"]:
        if chat_id in user_last_location:
            lat, lon = user_last_location[chat_id]["lat"], user_last_location[chat_id]["lon"]
            answer = get_address(lat, lon, user_lang.get(chat_id, "ru"))
            send_message(chat_id, f"📍 {answer}", get_pet_only_keyboard())
            text_to_voice_yandex(answer, chat_id)
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
            lang_name = "Русский"
        elif lang == "en":
            lang_name = "English"
        else:
            lang_name = "中文"
        send_message(chat_id, f"✅ *Язык выбран: {lang_name}*")
        send_message(chat_id, "📍 Отправь геопозицию", get_location_reply_keyboard())
    
    elif data.startswith("booking_"):
        place_name = data.replace("booking_", "")
        send_message(chat_id, f"📞 *Бронирование в «{place_name}»*\n\n🔧 Функция бронирования в разработке. Скоро здесь можно будет забронировать столик прямо через DeVox!\n\nПока что вы можете построить маршрут до места.", get_pet_only_keyboard())
    
    elif data == "pet":
        handle_pet(chat_id)

def handle_location(chat_id, lat, lon):
    user_last_location[chat_id] = {"lat": lat, "lon": lon}
    user_has_location[chat_id] = True
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "", "reply_markup": {"remove_keyboard": True}})
    send_welcome_and_places(chat_id, lat, lon)

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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print("=" * 50)
    print("🤖 DeVox запущен на Render!")
    print("✅ Бот отвечает на вопросы о путешествиях, транспорте, еде и о себе")
    print("✅ Погода на сегодня, завтра, послезавтра и неделю")
    print("✅ Рекомендации мест с AI-подсказками")
    print("✅ Кнопки маршрута и бронирования")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port)
