import requests
from config import OPENWEATHER_API_KEY, DHAKA_CITY

def get_dhaka_weather():
    """ঢাকার আবহাওয়া তথ্য আনে OpenWeatherMap থেকে"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={DHAKA_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('cod') != 200:
            return None

        temp        = round(data['main']['temp'])
        feels_like  = round(data['main']['feels_like'])
        humidity    = data['main']['humidity']
        description = data['weather'][0]['description']
        wind_speed  = data['wind']['speed']

        return {
            'temp':        temp,
            'feels_like':  feels_like,
            'humidity':    humidity,
            'description': description,
            'wind_speed':  wind_speed,
            'rain_chance': get_rain_chance(),
        }
    except Exception as e:
        print(f"⚠️ আবহাওয়া ত্রুটি: {e}")
        return None


def get_rain_chance():
    """আগামী কয়েক ঘণ্টায় বৃষ্টির সম্ভাবনা (%)"""
    url = (
        f"http://api.openweathermap.org/data/2.5/forecast"
        f"?q={DHAKA_CITY}&appid={OPENWEATHER_API_KEY}&units=metric&cnt=4"
    )
    try:
        data = requests.get(url, timeout=10).json()
        rainy = sum(
            1 for item in data.get('list', [])
            if item['weather'][0]['main'] in ('Rain', 'Thunderstorm', 'Drizzle')
        )
        return int((rainy / 4) * 100)
    except Exception:
        return 0


def weather_advice(weather: dict) -> str:
    """আবহাওয়া অনুযায়ী পরামর্শ তৈরি করে"""
    if not weather:
        return "⚠️ আবহাওয়া তথ্য পাওয়া যাচ্ছে না।"

    if weather['temp'] >= 38:
        return "🔥 অসহ্য গরম! সকাল ৮টার আগে বা সন্ধ্যা ৬টার পরে বের হন। পানি ও ছাতা সাথে নিন!"
    elif weather['temp'] >= 34:
        return "☀️ বেশ গরম। ছাতা ও পানি সাথে নিন।"
    elif weather['rain_chance'] >= 70:
        return "🌧️ আজ ভারী বৃষ্টি হতে পারে! আগেভাগে বের হন, ছাতা নিন।"
    elif weather['rain_chance'] >= 40:
        return "🌦️ বৃষ্টি হতে পারে। ছাতা সাথে রাখুন।"
    else:
        return "✅ আবহাওয়া মোটামুটি ভালো। নিরাপদে বের হতে পারেন।"
