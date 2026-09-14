import sys
import os
import schedule
import time
import threading
from datetime import datetime
from dotenv import load_dotenv

# .env ফাইল লোড করা (PC-তে চললে)
load_dotenv()


# উইন্ডোজ কনসোলে বাংলা ও ইমোজি সাপোর্ট নিশ্চিত করা
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config import ALERT_TIMES
from email_sender import send_alert_email
from telegram_bot import run_telegram_bot


def email_scheduler():
    """পর্দার পেছনে চলে — নির্দিষ্ট সময়ে ইমেইল পাঠায়"""
    for t in ALERT_TIMES:
        schedule.every().day.at(t).do(send_alert_email)

    print(f"📧 Gmail শিডিউল সেট হয়েছে: {', '.join(ALERT_TIMES)}")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    print("=" * 55)
    print("  ঢাকা ট্রান্সপোর্ট এআই এজেন্ট বট চালু হচ্ছে...")
    print("=" * 55)
    print(f"  শুরুর সময়: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}")
    print("-" * 55)

    # স্টার্টআপ টেস্ট ইমেইল
    print("📧 স্টার্টআপ টেস্ট ইমেইল পাঠানো হচ্ছে...")
    try:
        send_alert_email()
    except Exception as e:
        print(f"ইমেইল পাঠাতে সমস্যা: {e}")

    # ইমেইল শিডিউলার আলাদা থ্রেডে চালু
    t = threading.Thread(target=email_scheduler, daemon=True)
    t.start()

    # Telegram বট মেইন থ্রেডে চালু
    print("-" * 55)
    run_telegram_bot()


if __name__ == "__main__":
    main()
