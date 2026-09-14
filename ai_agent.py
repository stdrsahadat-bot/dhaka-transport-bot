import google.generativeai as genai
from config import GEMINI_API_KEY
from jam_analyzer import get_jam_status
from weather import get_dhaka_weather

genai.configure(api_key=GEMINI_API_KEY)

active_sessions = {}

SYSTEM_PROMPT = """তুমি একজন অভিজ্ঞ, বাস্তববাদী ও অত্যন্ত বিনয়ী ঢাকার পরিবহন এআই এজেন্ট ("ঢাকা গাইড")।
তোমার সাথে ক্লায়েন্ট স্বাভাবিক ভাষায় চ্যাট করবে। 

তোমার পরিচয় (কেউ জিজ্ঞেস করলে):
আমি "ঢাকা গাইড" — একটি বাংলাদেশি এআই ট্রান্সপোর্ট সহকারী। আমাকে তৈরি করেছেন Md Sahadat Hossain। আমার কাজ হলো ঢাকায় যাতায়াতকারী মানুষদের বাস রুট, মেট্রোরেল, সিএনজি ভাড়া ও ট্রাফিক পরিস্থিতি সম্পর্কে সংক্ষেপে ও সঠিকভাবে সহায়তা করা। আমি Google-এর Gemini AI প্রযুক্তি ব্যবহার করে কথা বলি।

তোমার নিয়মাবলি:
১. প্রথম বার্তা বা শুরু:
   ক্লায়েন্ট কোথা থেকে কোথায় যাবে তা সহজে জেনে নিয়ে ঢাকার বাস্তবসম্মত রুট, বাস, মেট্রো ও সিএনজি ভাড়া সংক্ষেপে ৩-৪টি বুলেট পয়েন্টে জানাও।
২. সংক্ষেপ ও কার্যকর:
   রাস্তার মানুষের সময় কম, তাই লম্বা গল্প নয়—বুলেট পয়েন্টে সময়, বাসের নাম, মেট্রো ও ভাড়ার সঠিক হিসাব দাও।
৩. কথোপকথন সমাপ্তি ও বিদায় (Wrap-up):
   যখন ক্লায়েন্ট তার প্রশ্নের সমাধান পেয়ে যাবে (বা বলবে 'ধন্যবাদ', 'থ্যাংকস', 'ঠিক আছে', 'বুঝেছি', 'আর লাগবে না' ইত্যাদি):
   তখন অত্যন্ত আন্তরিকভাবে বিদায় জানাও।
   (যেমন: "ঢাকা গাইড থেকে সহায়তা নেওয়ার জন্য আপনাকে অনেক ধন্যবাদ! আপনার যাত্রা নিরাপদ ও শুভ হোক। যেকোনো সময় আবার আসবেন। শুভকামনা! 💚")
   এবং শেষে যোগ করো: [SESSION_COMPLETE]
"""

MODEL_NAME = 'models/gemini-3.5-flash-lite'

def get_or_create_chat(uid: int):
    if uid not in active_sessions:
        try:
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=SYSTEM_PROMPT
            )
            active_sessions[uid] = model.start_chat(history=[])
        except Exception as e:
            print(f"Failed to start chat: {e}")
    return active_sessions.get(uid)

def get_ai_response(uid: int, msg: str) -> dict:
    """এআই উত্তর প্রদান করে এবং সেশন শেষ কি না তা জানায়"""
    jam = get_jam_status()
    w = get_dhaka_weather()
    
    context_data = f"[বর্তমান ট্রাফিক: {jam['level']}]"
    if w:
        context_data += f" [আবহাওয়া: {w['temp']}°C, বৃষ্টি: {w['rain_chance']}%]"
    
    prompt = f"[লাইভ ডাটা: {context_data}]\nক্লায়েন্ট: {msg}"

    chat = get_or_create_chat(uid)
    if chat:
        try:
            response = chat.send_message(prompt)
            if response and response.text:
                text = response.text
                is_complete = False
                if "[SESSION_COMPLETE]" in text:
                    text = text.replace("[SESSION_COMPLETE]", "").strip()
                    is_complete = True
                    active_sessions.pop(uid, None) # সেশন শেষ
                return {"reply": text, "is_complete": is_complete}
        except Exception as e:
            print(f"Chat error: {e}")
            active_sessions.pop(uid, None)

    return {
        "reply": f"📍 বর্তমান ট্রাফিক: {jam['level']} | 🌡️ আবহাওয়া: {w['temp'] if w else '৩০'}°C\n\nআপনি ঠিক কোথা থেকে কোথায় যেতে চান জানান, আমি রুট ও ভাড়া বলে দিচ্ছি।",
        "is_complete": False
    }

def clear_history(uid: int):
    active_sessions.pop(uid, None)
