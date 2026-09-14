import os
import json
import re
import smtplib
import threading
import time
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


def trigger_welcome_email_async(email: str):
    """ব্লক না করে ব্যাকগ্রাউন্ড থ্রেডে ওয়েলকাম ইমেইল পাঠানো"""
    t = threading.Thread(target=send_welcome_email, args=(email,), daemon=True)
    t.start()


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
            trigger_welcome_email_async(email)
            return True, (
                f"✅ **আপনার ইমেইল সফলভাবে আপডেট করা হয়েছে:** `{email}`\n\n"
                "📬 **প্রমাণস্বরূপ এইমাত্র একটি লাইভ টেস্ট বুলেটিন আপনার জিমেইলে পাঠানো হয়েছে!**\n\n"
                "⚠️ **ইনবক্সে খুঁজে না পেলে:**\n"
                "যেহেতু নতুন সার্ভিস থেকে প্রথমবার বার্তা পাঠানো হচ্ছে, তাই আপনার জিমেইল অ্যাপের বাঁদিকের মেনু (≡) থেকে **Spam (স্প্যাম)** অথবা **Promotions / Updates** ফোল্ডার চেক করুন। সেখানে পেলে দয়া করে **'Report not spam'** বা ইনবক্সে স্থানান্তর করুন—তাহলে পরবর্তী সব বুলেটিন সরাসরি মূল ইনবক্সে আসবে।\n\n"
                "⏰ প্রতিদিন **সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায়** স্বয়ংক্রিয়ভাবে বুলেটিন আপনার ইনবক্সে পৌঁছে যাবে!"
            )

    subs.append({
        "email": email,
        "chat_id": chat_id,
        "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_subscribers(subs)
    trigger_welcome_email_async(email)
    return True, (
        f"🎉 **অভিনন্দন! আপনার ইমেইল সফলভাবে যুক্ত হয়েছে:**\n`{email}`\n\n"
        "📬 **প্রমাণস্বরূপ এইমাত্র একটি লাইভ টেস্ট বুলেটিন আপনার জিমেইলে পাঠানো হয়েছে!**\n\n"
        "⚠️ **ইনবক্সে খুঁজে না পেলে করণীয়:**\n"
        "যেহেতু এটি স্বয়ংক্রিয় বুলেটিন এবং আপনি প্রথমবার যুক্ত হলেন, তাই আপনার জিমেইল অ্যাপের বাঁদিকের মেনু (≡) থেকে **Spam (স্প্যাম)** অথবা **Promotions / Updates** ফোল্ডার চেক করুন। সেখানে পেলে দয়া করে **'Report not spam'** করে নিন, তাহলে পরবর্তী সব বুলেটিন সরাসরি ইনবক্সে আসবে।\n\n"
        "⏰ এরপর থেকে প্রতিদিন **সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায়** ঢাকার সর্বশেষ ট্রাফিক ও আবহাওয়া বুলেটিন স্বয়ংক্রিয়ভাবে আপনার ইনবক্সে পৌঁছে যাবে!"
    )


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
    date_str = now.strftime('%d %B, %Y | %I:%M %p')

    # জ্যামের স্ট্যাটাস অনুযায়ী আধুনিক কালার প্যালেট
    jam_lvl = jam.get('level', '')
    if "তীব্র" in jam_lvl or "অসহনীয়" in jam_lvl or "ভারী" in jam_lvl:
        jam_badge_bg = "#FEE2E2"
        jam_badge_color = "#991B1B"
        jam_border = "#F87171"
        jam_icon = "🔴"
    elif "সহনীয়" in jam_lvl or "মাঝারি" in jam_lvl:
        jam_badge_bg = "#FEF3C7"
        jam_badge_color = "#92400E"
        jam_border = "#FBBF24"
        jam_icon = "🟡"
    else:
        jam_badge_bg = "#DCFCE7"
        jam_badge_color = "#166534"
        jam_border = "#4ADE80"
        jam_icon = "🟢"

    if weather:
        temp = f"{weather['temp']}°C"
        feels_like = f"{weather['feels_like']}°C"
        humidity = f"{weather['humidity']}%"
        rain_chance = f"{weather['rain_chance']}%"
        weather_desc = weather.get('description', 'স্বাভাবিক আবহাওয়া')
    else:
        temp = "স্বাভাবিক"
        feels_like = "স্বাভাবিক"
        humidity = "--"
        rain_chance = "০%"
        weather_desc = "আপডেট হচ্ছে"

    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ঢাকা লাইভ ট্রাফিক ও আবহাওয়া বুলেটিন</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; color: #1E293B;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 30px 12px;">
    <tr>
      <td align="center">
        <!-- Main Email Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; background: #FFFFFF; border-radius: 24px; overflow: hidden; box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08); border: 1px solid #E2E8F0;">
          
          <!-- Ultra-Modern Gradient Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #0D9488 100%); padding: 38px 28px; text-align: center;">
              <div style="display: inline-block; background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.25); color: #38BDF8; font-size: 11px; font-weight: 700; padding: 5px 15px; border-radius: 50px; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px;">
                🇧🇩 DHAKA TRANSPORT AI BULLETIN
              </div>
              <h1 style="color: #FFFFFF; margin: 0 0 8px 0; font-size: 25px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.3;">
                {g_emoji} {greeting}, ঢাকা!
              </h1>
              <p style="color: #94A3B8; margin: 0; font-size: 13px; font-weight: 500;">
                📅 {date_str}
              </p>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding: 28px 24px;">

              <!-- Live Traffic Card -->
              <div style="background: #FFFFFF; border: 1.5px solid {jam_border}; border-radius: 18px; padding: 20px; margin-bottom: 22px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                <div style="margin-bottom: 12px;">
                  <span style="font-size: 16px; font-weight: 800; color: #0F172A;">🚗 ট্রাফিক ও লাইভ জ্যাম পরিস্থিতি</span>
                </div>
                
                <div style="background: {jam_badge_bg}; color: {jam_badge_color}; border: 1px solid {jam_border}; display: inline-block; padding: 6px 14px; border-radius: 30px; font-size: 14px; font-weight: 700; margin-bottom: 12px;">
                  {jam_icon} বর্তমান অবস্থা: {jam['level']}
                </div>
                
                <p style="margin: 0 0 8px 0; color: #334155; font-size: 14px; line-height: 1.6;">
                  • <b>পরামর্শ:</b> {jam['advice']}
                </p>
                <p style="margin: 0; color: #64748B; font-size: 13px; line-height: 1.5;">
                  • ⏱️ <b>রওয়ানা হওয়ার দিকনির্দেশনা:</b> {depart}
                </p>
              </div>

              <!-- Weather Card -->
              <div style="background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%); border: 1.5px solid #A7F3D0; border-radius: 18px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                <div style="margin-bottom: 14px;">
                  <span style="font-size: 16px; font-weight: 800; color: #065F46;">🌤️ আজকের আবহাওয়া ও পূর্বাভাস</span>
                  <span style="float: right; font-size: 13px; color: #059669; font-weight: 600;">{weather_desc}</span>
                </div>

                <!-- Weather Stats Grid -->
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 14px;">
                  <tr>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">তাপমাত্রা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0F172A; margin-top: 4px;">{temp}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">অনুভূত</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0F172A; margin-top: 4px;">{feels_like}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">আর্দ্রতা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0284C7; margin-top: 4px;">{humidity}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">বৃষ্টির শঙ্কা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #2563EB; margin-top: 4px;">{rain_chance}</div>
                    </td>
                  </tr>
                </table>

                <div style="background: #ECFDF5; border-radius: 12px; padding: 10px 14px; border: 1px solid #A7F3D0;">
                  <p style="margin: 0; color: #065F46; font-size: 13px; line-height: 1.5;">
                    💡 <b>আবহাওয়া সতর্কতা:</b> {w_advice}
                  </p>
                </div>
              </div>

              <!-- Interactive Telegram CTA Button -->
              <div style="text-align: center; margin: 26px 0 10px 0;">
                <a href="{TELEGRAM_BOT_URL}" style="background: linear-gradient(135deg, #0088CC 0%, #00B4D8 100%); color: #FFFFFF; text-decoration: none; padding: 14px 32px; border-radius: 35px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 6px 20px rgba(0, 136, 204, 0.35); letter-spacing: 0.3px;">
                  💬 বাসের রুট বা মেট্রোরেল ভাড়া খুঁজুন
                </a>
              </div>

            </td>
          </tr>

          <!-- Modern Dark Footer -->
          <tr>
            <td style="background: #0F172A; padding: 26px 24px; text-align: center; color: #94A3B8; font-size: 12px; line-height: 1.7;">
              <p style="margin: 0 0 6px 0; color: #F1F5F9; font-weight: 700; font-size: 13px;">
                ঢাকা ট্রান্সপোর্ট এআই অ্যাসিস্ট্যান্ট প্ল্যাটফর্ম 🇧🇩
              </p>
              <p style="margin: 0 0 12px 0;">
                👑 প্রতিষ্ঠাতা ও ক্রিয়েটর: <span style="color: #38BDF8; font-weight: 700;">Md Sahadat Hossain</span>
              </p>
              <p style="margin: 0; font-size: 11px; color: #64748B;">
                প্রতিদিন সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায় এই বুলেটিন পাঠানো হয়।<br>
                অ্যালার্ট বন্ধ করতে চাইলে টেলিগ্রাম বটে গিয়ে <span style="color: #94A3B8; font-family: monospace;">/unsubscribe</span> লিখুন।
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_welcome_email(recipient_email: str) -> bool:
    """সাবস্ক্রাইব করার পর তাৎক্ষণিক প্রিমিয়াম লাইভ স্যাম্পল বুলেটিন পাঠানো (প্রমাণস্বরূপ)"""
    now = datetime.now()
    weather = get_dhaka_weather()
    jam = get_jam_status()
    depart = get_departure_advice()
    w_advice = weather_advice(weather)
    date_str = now.strftime('%d %B, %Y | %I:%M %p')

    # জ্যামের কালার
    jam_lvl = jam.get('level', '')
    if "তীব্র" in jam_lvl or "অসহনীয়" in jam_lvl or "ভারী" in jam_lvl:
        jam_badge_bg = "#FEE2E2"
        jam_badge_color = "#991B1B"
        jam_border = "#F87171"
        jam_icon = "🔴"
    elif "সহনীয়" in jam_lvl or "মাঝারি" in jam_lvl:
        jam_badge_bg = "#FEF3C7"
        jam_badge_color = "#92400E"
        jam_border = "#FBBF24"
        jam_icon = "🟡"
    else:
        jam_badge_bg = "#DCFCE7"
        jam_badge_color = "#166534"
        jam_border = "#4ADE80"
        jam_icon = "🟢"

    if weather:
        temp = f"{weather['temp']}°C"
        feels_like = f"{weather['feels_like']}°C"
        humidity = f"{weather['humidity']}%"
        rain_chance = f"{weather['rain_chance']}%"
        weather_desc = weather.get('description', 'স্বাভাবিক আবহাওয়া')
    else:
        temp = "স্বাভাবিক"
        feels_like = "স্বাভাবিক"
        humidity = "--"
        rain_chance = "০%"
        weather_desc = "আপডেট হচ্ছে"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🌟 ঢাকা ট্রাফিক ও আবহাওয়া বুলেটিন সক্রিয় হয়েছে [লাইভ স্যাম্পল]"
    msg['From'] = f"Dhaka Transport Guide <{GMAIL_ADDRESS}>"
    msg['To'] = recipient_email
    msg['Reply-To'] = GMAIL_ADDRESS

    plain_text = f"""ঢাকা ট্রাফিক ও আবহাওয়া বুলেটিন [লাইভ স্যাম্পল]
───────────────────────────
স্বাগতম! আপনার ইমেইল সফলভাবে ঢাকা ট্রান্সপোর্ট সার্ভিসে সাবস্ক্রাইব হয়েছে।

🚗 বর্তমান ট্রাফিক অবস্থা: {jam.get('level', 'স্বাভাবিক')}
• পরামর্শ: {jam.get('advice', '')}
• রওয়ানা হওয়ার দিকনির্দেশনা: {depart}

🌤️ আজকের আবহাওয়া:
• তাপমাত্রা: {temp} (অনুভূত: {feels_like})
• আর্দ্রতা: {humidity} | বৃষ্টির সম্ভাবনা: {rain_chance}
• সতর্কবার্তা: {w_advice}

⏰ প্রতিদিন সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায় এই বুলেটিন আপনার ইনবক্সে পৌঁছাবে।

ধন্যবাদ,
ঢাকা ট্রান্সপোর্ট এআই অ্যাসিস্ট্যান্ট প্ল্যাটফর্ম 🇧🇩
প্রতিষ্ঠাতা ও ক্রিয়েটর: Md Sahadat Hossain
টেলিগ্রাম বট লিংক: {TELEGRAM_BOT_URL}
"""

    html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ঢাকা লাইভ ট্রাফিক ও আবহাওয়া বুলেটিন</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; color: #1E293B;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 30px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; background: #FFFFFF; border-radius: 24px; overflow: hidden; box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08); border: 1px solid #E2E8F0;">
          
          <!-- Gradient Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #0D9488 100%); padding: 36px 28px; text-align: center;">
              <div style="display: inline-block; background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); color: #38BDF8; font-size: 11px; font-weight: 700; padding: 5px 15px; border-radius: 50px; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px;">
                🎉 SUBSCRIPTION ACTIVATED ✅
              </div>
              <h1 style="color: #FFFFFF; margin: 0 0 8px 0; font-size: 23px; font-weight: 800; letter-spacing: -0.5px;">
                স্বাগতম! আপনার বুলেটিন সফলভাবে সক্রিয় হয়েছে
              </h1>
              <p style="color: #94A3B8; margin: 0; font-size: 13px;">
                📅 {date_str}
              </p>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding: 28px 24px;">
              <!-- Welcome Proof Box -->
              <div style="background: linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%); border-radius: 16px; padding: 16px 20px; border: 1.5px solid #BAE6FD; margin-bottom: 22px;">
                <p style="margin: 0 0 6px 0; font-size: 15px; font-weight: 700; color: #0369A1;">
                  📬 ইনস্ট্যান্ট লাইভ প্রুফ বুলেটিন
                </p>
                <p style="margin: 0; font-size: 13px; color: #334155; line-height: 1.6;">
                  আপনার ইমেইল (<b style="color: #0284C7;">{recipient_email}</b>) সফলভাবে নিবন্ধিত হয়েছে। প্রমাণ হিসেবে এইমাত্র লাইভ ডেটা দিয়ে প্রস্তুত আপনার প্রথম স্যাম্পল বুলেটিন নিচে দেওয়া হলো:
                </p>
              </div>

              <!-- Live Traffic Card -->
              <div style="background: #FFFFFF; border: 1.5px solid {jam_border}; border-radius: 18px; padding: 20px; margin-bottom: 22px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                <div style="margin-bottom: 12px;">
                  <span style="font-size: 16px; font-weight: 800; color: #0F172A;">🚗 বর্তমান ঢাকা ট্রাফিক ও জ্যাম পরিস্থিতি</span>
                </div>
                
                <div style="background: {jam_badge_bg}; color: {jam_badge_color}; border: 1px solid {jam_border}; display: inline-block; padding: 6px 14px; border-radius: 30px; font-size: 14px; font-weight: 700; margin-bottom: 12px;">
                  {jam_icon} বর্তমান অবস্থা: {jam['level']}
                </div>
                
                <p style="margin: 0 0 8px 0; color: #334155; font-size: 14px; line-height: 1.6;">
                  • <b>পরামর্শ:</b> {jam['advice']}
                </p>
                <p style="margin: 0; color: #64748B; font-size: 13px; line-height: 1.5;">
                  • ⏱️ <b>রওয়ানা হওয়ার দিকনির্দেশনা:</b> {depart}
                </p>
              </div>

              <!-- Weather Card -->
              <div style="background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%); border: 1.5px solid #A7F3D0; border-radius: 18px; padding: 20px; margin-bottom: 22px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                <div style="margin-bottom: 14px;">
                  <span style="font-size: 16px; font-weight: 800; color: #065F46;">🌤️ বর্তমান ঢাকা আবহাওয়া</span>
                  <span style="float: right; font-size: 13px; color: #059669; font-weight: 600;">{weather_desc}</span>
                </div>

                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 14px;">
                  <tr>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">তাপমাত্রা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0F172A; margin-top: 4px;">{temp}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">অনুভূত</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0F172A; margin-top: 4px;">{feels_like}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">আর্দ্রতা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #0284C7; margin-top: 4px;">{humidity}</div>
                    </td>
                    <td width="2%"></td>
                    <td width="23%" style="text-align: center; padding: 10px 4px; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;">
                      <div style="font-size: 11px; color: #64748B; font-weight: 600;">বৃষ্টির শঙ্কা</div>
                      <div style="font-size: 17px; font-weight: 800; color: #2563EB; margin-top: 4px;">{rain_chance}</div>
                    </td>
                  </tr>
                </table>

                <div style="background: #ECFDF5; border-radius: 12px; padding: 10px 14px; border: 1px solid #A7F3D0;">
                  <p style="margin: 0; color: #065F46; font-size: 13px; line-height: 1.5;">
                    💡 <b>আবহাওয়া সতর্কতা:</b> {w_advice}
                  </p>
                </div>
              </div>

              <!-- Schedule Box -->
              <div style="background: #F8FAFC; border-radius: 14px; padding: 16px 20px; border: 1px solid #E2E8F0; margin-bottom: 24px;">
                <p style="margin: 0 0 8px 0; font-weight: 700; color: #0F172A; font-size: 14px;">
                  ⏰ এর পর থেকে প্রতিদিন কখন আপডেট পাবেন:
                </p>
                <div style="font-size: 13px; color: #475569; line-height: 1.8;">
                  • 🌅 <b>সকাল ০৭:০০ টা:</b> অফিসে বা কাজে বের হওয়ার আগের আপডেট<br>
                  • ☀️ <b>দুপুর ১২:০০ টা:</b> মধ্যাহ্ন ট্রাফিক ও আবহাওয়া আপডেট<br>
                  • 🌆 <b>সন্ধ্যা ০৬:০০ টা:</b> অফিস শেষে বাড়ি ফেরার রুট সতর্কতা
                </div>
              </div>

              <!-- CTA Button -->
              <div style="text-align: center; margin: 20px 0 10px 0;">
                <a href="{TELEGRAM_BOT_URL}" style="background: linear-gradient(135deg, #0088CC 0%, #00B4D8 100%); color: #FFFFFF; text-decoration: none; padding: 14px 32px; border-radius: 35px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 6px 20px rgba(0, 136, 204, 0.35);">
                  💬 বাসের রুট বা মেট্রোরেল ভাড়া খুঁজুন
                </a>
              </div>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #0F172A; padding: 24px; text-align: center; color: #94A3B8; font-size: 12px; line-height: 1.7;">
              <p style="margin: 0 0 6px 0; color: #F1F5F9; font-weight: 700;">
                ঢাকা ট্রান্সপোর্ট এআই প্ল্যাটফর্ম 🇧🇩
              </p>
              <p style="margin: 0 0 10px 0;">
                👑 প্রতিষ্ঠাতা ও ক্রিয়েটর: <span style="color: #38BDF8; font-weight: 700;">Md Sahadat Hossain</span>
              </p>
              <p style="margin: 0; font-size: 11px; color: #64748B;">
                অ্যালার্ট বন্ধ করতে চাইলে টেলিগ্রাম বটে গিয়ে /unsubscribe লিখুন।
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    for attempt in range(2):
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=25) as server:
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_bytes())
            print(f"✅ স্বাগতম ও লাইভ স্যাম্পল ইমেইল পাঠানো হয়েছে to {recipient_email}")
            return True
        except Exception as e:
            print(f"⚠️ স্বাগতম ইমেইল পাঠাতে চেষ্টা {attempt + 1} ব্যর্থ: {e}")
            if attempt == 0:
                time.sleep(2)
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
