import os
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
from weather import get_dhaka_weather, weather_advice
from jam_analyzer import get_jam_status, get_departure_advice

# টেলিগ্রাম বটের সরাসরি লিংক
TELEGRAM_BOT_URL = "https://t.me/dhaka_transport_bot"

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")


# ────────────────────── সাবস্ক্রাইবার ডাটাবেজ ──────────────────────
def load_subscribers() -> list:
    """সাবস্ক্রাইবার তালিকা লোড করা"""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading subscribers: {e}")
    return []


def save_subscribers(sub_list: list):
    """সাবস্ক্রাইবার তালিকা ফাইলে সংরক্ষণ করা"""
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sub_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving subscribers: {e}")


def is_valid_email(email: str) -> bool:
    """ইমেইল ফরম্যাট সঠিক কি না যাচাই"""
    regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(regex, email.strip()))


def add_subscriber(email: str, chat_id: int) -> tuple[bool, str]:
    """নতুন ইমেইল সাবস্ক্রাইবার যোগ করা"""
    email = email.strip().lower()
    if not is_valid_email(email):
        return False, "⚠️ দুঃখিত! ইমেইল ঠিকানাটি সঠিক মনে হচ্ছে না। অনুগ্রহ করে সঠিক ইমেইল লিখুন (যেমন: name@gmail.com)।"

    subs = load_subscribers()
    for s in subs:
        if s.get("email") == email:
            return False, f"ℹ️ এই ইমেইল ({email}) ইতিমধ্যে আমাদের দৈনিক অ্যালার্ট সার্ভিসে সাবস্ক্রাইব করা আছে!"
        if s.get("chat_id") == chat_id:
            s["email"] = email
            s["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_subscribers(subs)
            send_welcome_email(email)
            return True, f"✅ আপনার ইমেইল সফলভাবে আপডেট করা হয়েছে: **{email}**\nপ্রতিদিন সকাল ৭টা, দুপুর ১২টা ও সন্ধ্যা ৬টায় আপডেট পেয়ে যাবেন!"

    subs.append({
        "email": email,
        "chat_id": chat_id,
        "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_subscribers(subs)
    send_welcome_email(email)
    return True, f"🎉 **অভিনন্দন!**\nআপনার ইমেইল (**{email}**) সফলভাবে সাবস্ক্রাইব করা হয়েছে।\n\nপ্রতিদিন **সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায়** ঢাকার লাইভ ট্রাফিক ও আবহাওয়া বুলেটিন সরাসরি আপনার ইনবক্সে পৌঁছে যাবে!"


def remove_subscriber(chat_id: int) -> tuple[bool, str]:
    """সাবস্ক্রিপশন বাতিল করা"""
    subs = load_subscribers()
    initial_len = len(subs)
    remaining = [s for s in subs if s.get("chat_id") != chat_id]
    if len(remaining) < initial_len:
        save_subscribers(remaining)
        return True, "❌ আপনার ইমেইল সাবস্ক্রিপশন সফলভাবে বাতিল করা হয়েছে। আর কোনো ইমেইল পাঠানো হবে না। যেকোনো সময় আবার যুক্ত হতে পারবেন!"
    return False, "ℹ️ আপনার কোনো সক্রিয় ইমেইল সাবস্ক্রিপশন খুঁজে পাওয়া যায়নি।"


def get_all_recipients() -> list:
    """সকল প্রাপকের ইমেইল তালিকা (Sahadat vai + সকল গ্রাহক)"""
    recipients = set()
    if RECIPIENT_EMAIL:
        recipients.add(RECIPIENT_EMAIL.strip().lower())
    for s in load_subscribers():
        if s.get("email"):
            recipients.add(s["email"].strip().lower())
    return list(recipients)


# ────────────────────── ইমেইল টেমপ্লেট ও জেনারেশন ──────────────────
def _greeting():
    h = datetime.now().hour
    if h < 12:
        return "সুপ্রভাত", "🌅"
    elif h < 17:
        return "শুভ দুপুর", "☀️"
    else:
        return "শুভ সন্ধ্যা", "🌆"


def _build_html() -> str:
    greeting, g_emoji = _greeting()
    now     = datetime.now()
    weather = get_dhaka_weather()
    jam     = get_jam_status()
    depart  = get_departure_advice()
    w_advice = weather_advice(weather)

    if weather:
        weather_html = f"""
        <p>🌡️ তাপমাত্রা: <b>{weather['temp']}°C</b> (অনুভূত হচ্ছে {weather['feels_like']}°C)</p>
        <p>💧 আর্দ্রতা: {weather['humidity']}%</p>
        <p>🌤️ আকাশ: {weather['description']}</p>
        <p>🌧️ বৃষ্টির সম্ভাবনা: {weather['rain_chance']}%</p>
        """
        w_color = "#FFEBEE" if weather['temp'] >= 38 else \
                  "#FFF3E0" if weather['rain_chance'] >= 40 else "#E8F5E9"
        w_border = "#F44336" if weather['temp'] >= 38 else \
                   "#FF9800" if weather['rain_chance'] >= 40 else "#4CAF50"
    else:
        weather_html = "<p>⚠️ আবহাওয়ার তথ্য এই মুহূর্তে আপডেট হচ্ছে।</p>"
        w_color = "#F5F5F5"
        w_border = "#9E9E9E"

    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #F4F6F9; margin:0; padding:20px; color:#333; }}
  .card {{ max-width:600px; margin:0 auto; background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 18px rgba(0,0,0,0.08); }}
  .hdr {{ background:linear-gradient(135deg, #006A4E 0%, #11998e 100%); color:#fff; padding:24px; text-align:center; }}
  .hdr h1 {{ margin:0; font-size:22px; }}
  .hdr p {{ margin:5px 0 0; opacity:0.9; font-size:14px; }}
  .cnt {{ padding:22px; }}
  .bx {{ border-radius:10px; padding:14px 18px; margin-bottom:16px; border-left:5px solid; }}
  .bx h3 {{ margin:0 0 8px; font-size:16px; display:flex; align-items:center; gap:8px; }}
  .bx p {{ margin:4px 0; font-size:14px; line-height:1.5; }}
  .jam-bx {{ background:{jam['color']}18; border-left-color:{jam['color']}; }}
  .w-bx {{ background:{w_color}; border-left-color:{w_border}; }}
  .tip-bx {{ background:#EDE7F6; border-left-color:#673AB7; }}
  .btn-wrap {{ text-align:center; margin:25px 0 15px; }}
  .btn {{ background:#0088cc; color:#ffffff !important; text-decoration:none; padding:13px 26px; border-radius:30px; font-weight:bold; font-size:15px; display:inline-block; box-shadow:0 4px 12px rgba(0,136,204,0.3); }}
  .ft {{ background:#F9FAFB; border-top:1px solid #eee; padding:14px; text-align:center; font-size:12px; color:#777; }}
</style>
</head>
<body>
<div class="card">
  <div class="hdr">
    <h1>{g_emoji} {greeting}! ঢাকা ট্রাফিক ও আবহাওয়া আপডেট</h1>
    <p>📅 {now.strftime('%d %B, %Y | %I:%M %p')}</p>
  </div>
  <div class="cnt">
    <div class="bx jam-bx">
      <h3 style="color:{jam['color']};">🚗 ট্রাফিক পূর্বাভাস: {jam['level']}</h3>
      <p>• {jam['advice']}</p>
      <p>• {depart}</p>
    </div>
    <div class="bx w-bx">
      <h3 style="color:{w_border};">🌤️ আজকের ঢাকা আবহাওয়া</h3>
      {weather_html}
      <p><b>💡 পরামর্শ:</b> {w_advice}</p>
    </div>
    <div class="btn-wrap">
      <a href="{TELEGRAM_BOT_URL}" class="btn">💬 সরাসরি টেলিগ্রামে এআই এর সাথে কথা বলুন</a>
    </div>
  </div>
  <div class="ft">
    🚌 ঢাকা ট্রান্সপোর্ট এআই প্ল্যাটফর্ম | প্রতিষ্ঠাতা: Md Sahadat Hossain<br>
    জরুরি পুলিশ ও ট্রাফিক সেবা পেতে কল করুন ৯৯৯-এ
  </div>
</div>
</body>
</html>"""


def send_welcome_email(recipient_email: str) -> bool:
    """সাবস্ক্রাইব করার পর তাৎক্ষণিক স্বাগতম ইমেইল পাঠানো"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🎉 স্বাগতম! ঢাকা ট্রান্সপোর্ট দৈনিক অ্যালার্ট সার্ভিসে"
    msg['From']    = GMAIL_ADDRESS
    msg['To']      = recipient_email

    html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; background: #f4f6f8; padding: 20px;">
  <div style="max-width: 550px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
    <h2 style="color: #006A4E; margin-top: 0;">🎉 ঢাকা ট্রান্সপোর্ট এআই অ্যালার্টে স্বাগতম!</h2>
    <p>আস্সালামু আলাইকুম,</p>
    <p>আপনার ইমেইল (<b>{recipient_email}</b>) সফলভাবে আমাদের দৈনিক বুলেটিন সার্ভিসে নিবন্ধিত হয়েছে।</p>
    <div style="background: #E8F5E9; border-left: 4px solid #4CAF50; padding: 12px; border-radius: 6px; margin: 15px 0;">
      <p style="margin: 0; font-weight: bold; color: #2E7D32;">⏰ আপনি প্রতিদিন কখন আপডেট পাবেন:</p>
      <ul style="margin: 8px 0 0; padding-left: 20px; color: #333;">
        <li>সকাল ০৭:০০ টা (অফিস/কাজে যাওয়ার প্রস্তুতি)</li>
        <li>দুপুর ১২:০০ টা (মধ্যাহ্ন ট্রাফিক ও আবহাওয়া)</li>
        <li>সন্ধ্যা ০৬:০০ টা (বাসা ফেরার আগের আপডেট)</li>
      </ul>
    </div>
    <p>যেকোনো সময় বাসের রুট, ভাড়া বা মেট্রোরেলের তথ্য জানতে সরাসরি টেলিগ্রাম বটে কথা বলতে পারেন:</p>
    <div style="text-align: center; margin: 20px 0;">
      <a href="{TELEGRAM_BOT_URL}" style="background: #0088cc; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">টেলিগ্রাম বটে চ্যাট করুন</a>
    </div>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #888; text-align: center; margin-bottom: 0;">
      ঢাকা ট্রান্সপোর্ট এআই প্ল্যাটফর্ম | প্রতিষ্ঠাতা: Md Sahadat Hossain
    </p>
  </div>
</body>
</html>"""
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_bytes())
        print(f"✅ স্বাগতম ইমেইল পাঠানো হয়েছে to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ স্বাগতম ইমেইল পাঠাতে সমস্যা: {e}")
        return False


def send_alert_email() -> bool:
    """সকল সাবস্ক্রাইবারকে নির্ধারিত সময়ে অ্যালার্ট ইমেইল পাঠানো"""
    now = datetime.now()
    subject = f"🚌 ঢাকা ট্রাফিক ও আবহাওয়া আপডেট | {now.strftime('%d/%m/%Y %I:%M %p')}"
    recipients = get_all_recipients()

    if not recipients:
        print("⚠️ কোনো ইমেইল প্রাপক পাওয়া যায়নি।")
        return False

    html = _build_html()
    success_count = 0

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            for email in recipients:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From']    = GMAIL_ADDRESS
                    msg['To']      = email
                    msg.attach(MIMEText(html, 'html', 'utf-8'))
                    server.sendmail(GMAIL_ADDRESS, email, msg.as_bytes())
                    success_count += 1
                except Exception as sub_err:
                    print(f"Failed to send to {email}: {sub_err}")

        print(f"✅ সফলভাবে {success_count}/{len(recipients)} জনের জিমেইলে বুলেটিন পাঠানো হয়েছে [{now.strftime('%H:%M')}]")
        return True
    except Exception as e:
        print(f"❌ ইমেইল পাঠাতে সমস্যা: {e}")
        return False
