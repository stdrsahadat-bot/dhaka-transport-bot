from datetime import datetime

# ===================================================
# জ্যাম বিশ্লেষক — সময় ও দিন অনুযায়ী জ্যাম অনুমান
# ===================================================

PEAK_HOURS = {
    # (শুরু, শেষ): (স্তর, ইমোজি, পরামর্শ)
    (0,  6):  ("নেই বললেই চলে", "🟢", "ভোরবেলা — রাস্তা একদম ফাঁকা! এখনই বের হন।"),
    (7,  9):  ("ভারী",           "🔴", "অফিস টাইম জ্যাম! সম্ভব হলে মেট্রোতে যান।"),
    (10, 11): ("মাঝারি",         "🟡", "জ্যাম একটু কমেছে, বের হতে পারেন।"),
    (12, 14): ("মাঝারি",         "🟡", "দুপুরে মাঝারি জ্যাম। একটু পরে গেলে ভালো।"),
    (15, 20): ("ভয়াবহ",         "🔴", "বিকেল-সন্ধ্যার পিক আওয়ার! রাত ৮টার পর বের হন।"),
    (21, 22): ("মাঝারি",         "🟡", "জ্যাম কমতে শুরু করেছে।"),
    (23, 24): ("কম",             "🟢", "রাতে রাস্তা ফাঁকা, নিরাপদে যেতে পারবেন।"),
}

PROBLEM_AREAS = {
    (7,  9):  ["মিরপুর রোড", "ফার্মগেট", "মহাখালী", "যাত্রাবাড়ী", "গুলিস্তান"],
    (10, 14): ["গুলিস্তান", "পল্টন", "মতিঝিল"],
    (15, 20): ["শাহবাগ", "ফার্মগেট", "বনানী", "গুলশান", "মতিঝিল", "সায়েদাবাড়ী"],
    (21, 24): ["গুলিস্তান", "পল্টন"],
}

FRIDAY_STATUS = {
    (9, 13): ("মাঝারি", "🟡", "জুমার নামাজের সময় রাস্তা ব্যস্ত।"),
}


def _find_range(hour: int, table: dict):
    for (start, end), value in table.items():
        if start <= hour < end:
            return value
    return None


def get_jam_status() -> dict:
    now     = datetime.now()
    hour    = now.hour
    weekday = now.weekday()   # 0=সোম … 4=শুক্র, 5=শনি, 6=রবি
    is_friday = weekday == 4

    if is_friday:
        result = _find_range(hour, FRIDAY_STATUS)
        if result:
            level, emoji, advice = result
        else:
            level, emoji, advice = "কম", "🟢", "আজ শুক্রবার — রাস্তা মোটামুটি ফাঁকা।"
        return {
            'level': level, 'emoji': emoji, 'advice': advice,
            'problem_areas': ["গুলিস্তান", "সদরঘাট"] if is_friday else [],
        }

    if weekday == 5:  # শনিবার
        return {
            'level': "কম", 'emoji': "🟢",
            'advice': "আজ ছুটির দিন — রাস্তা ফাঁকা।",
            'problem_areas': [],
        }

    result = _find_range(hour, PEAK_HOURS)
    level, emoji, advice = result if result else ("কম", "🟢", "রাস্তা ফাঁকা।")
    areas  = _find_range(hour, PROBLEM_AREAS) or []

    return {'level': level, 'emoji': emoji, 'advice': advice, 'problem_areas': areas}


def get_departure_advice(jam_level: str = None) -> str:
    hour = datetime.now().hour
    if hour < 7:
        return "✅ এখনই বের হন — রাস্তা একদম ফাঁকা!"
    elif hour == 7:
        return "⚠️ জ্যাম শুরু হচ্ছে — দ্রুত বের হন!"
    elif 8 <= hour <= 9:
        return "🔴 এখন ভারী জ্যাম। ৩০-৪৫ মিনিট অপেক্ষা করুন অথবা মেট্রো নিন।"
    elif 10 <= hour <= 11:
        return "✅ এখন বের হতে পারেন — জ্যাম কম।"
    elif 12 <= hour <= 14:
        return "🟡 মাঝারি জ্যাম। সময় থাকলে একটু পরে যান।"
    elif hour == 15:
        return "⚠️ বিকেলের জ্যাম শুরু হচ্ছে — এখনই বের হন!"
    elif 16 <= hour <= 20:
        return "🔴 ভয়াবহ জ্যাম! রাত ৮টার পরে বের হওয়াই ভালো।"
    else:
        return "✅ এখন রাস্তা ফাঁকা — নিরাপদে যেতে পারবেন।"
