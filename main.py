import sys
import os
import schedule
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer

# .env ফাইল লোড করা (PC-তে চললে)
load_dotenv()

# ক্লাউড সার্ভারকে বাংলাদেশ সময় (BST / Asia/Dhaka) অনুযায়ী সেট করা
os.environ["TZ"] = "Asia/Dhaka"
if hasattr(time, "tzset"):
    try:
        time.tzset()
    except Exception:
        pass

# উইন্ডোজ কনসোলে বাংলা ও ইমোজি সাপোর্ট নিশ্চিত করা
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config import ALERT_TIMES
from email_sender import send_alert_email
from telegram_bot import run_telegram_bot


class HealthCheckHandler(BaseHTTPRequestHandler):
    """ক্লাউড সার্ভারের হেলথ চেক রেসপন্ডার (Railway/Render বন্ধ হওয়া রোধ করে)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"OK - Dhaka Transport AI Bot is Running 24/7!")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Health server note: {e}")


from ai_agent import cleanup_expired_sessions


def email_scheduler():
    """পর্দার পেছনে চলে — নির্দিষ্ট সময়ে ইমেইল পাঠায় এবং পুরানো সেশন ক্লিন করে"""
    for t in ALERT_TIMES:
        schedule.every().day.at(t).do(send_alert_email)

    # প্রতি ৬ ঘণ্টা পর পর পুরানো ২ দিনের নিষ্ক্রিয় সেশন মেমোরি থেকে মুছে দেওয়া
    schedule.every(6).hours.do(cleanup_expired_sessions)

    print(f"📧 Gmail শিডিউল সেট হয়েছে: {', '.join(ALERT_TIMES)}")
    print("🧹 অটো সেশন ক্লিনআপ শিডিউল সক্রিয় হয়েছে (প্রতি ৬ ঘণ্টায় চেক)")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    print("=" * 55)
    print("  ঢাকা ট্রান্সপোর্ট এআই এজেন্ট বট চালু হচ্ছে...")
    print("=" * 55)
    print(f"  শুরুর সময়: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}")
    print("-" * 55)

    # ক্লাউড হেলথ চেক সার্ভার চালু (যাতে Railway/Render ক্র্যাশ না করে)
    h_thread = threading.Thread(target=run_health_server, daemon=True)
    h_thread.start()

    # ইমেইল শিডিউলার আলাদা থ্রেডে চালু
    t = threading.Thread(target=email_scheduler, daemon=True)
    t.start()

    # Telegram বট মেইন থ্রেডে চালু
    print("-" * 55)
    run_telegram_bot()


if __name__ == "__main__":
    main()
