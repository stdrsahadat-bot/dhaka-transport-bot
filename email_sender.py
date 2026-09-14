import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
from weather import get_dhaka_weather, weather_advice
from jam_analyzer import get_jam_status, get_departure_advice

# টেলিগ্রাম বটের সরাসরি লিংক
TELEGRAM_BOT_URL = "https://t.me/dhaka_transport_bot"


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

    # আবহাওয়া সেকশন
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
        w_color, w_border = "#FFF3E0", "#FF9800"

    # জ্যাম সেকশন
    areas = ", ".join(jam['problem_areas']) if jam['problem_areas'] else "কোনো বিশেষ ট্রাফিক সমস্যা নেই"
    j_color  = "#FFEBEE" if jam['level'] in ("ভয়াবহ", "ভারী") else \
               "#FFF3E0" if jam['level'] == "মাঝারি" else "#E8F5E9"
    j_border = "#F44336" if jam['level'] in ("ভয়াবহ", "ভারী") else \
               "#FF9800" if jam['level'] == "মাঝারি" else "#4CAF50"

    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ঢাকা ট্রান্সপোর্ট ও আবহাওয়া বুলেটিন</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f4f8;padding:20px}}
    .wrap{{max-width:600px;margin:auto;background:#fff;border-radius:16px;overflow:hidden;
           box-shadow:0 6px 25px rgba(0,0,0,.1)}}
    .hd{{background:linear-gradient(135deg,#1565C0,#0D47A1);color:#fff;padding:28px 20px;text-align:center}}
    .hd h1{{font-size:22px;margin-bottom:6px}}
    .hd p{{font-size:14px;opacity:.9}}
    .sec{{padding:20px 25px;border-bottom:1px solid #edf2f7}}
    .sec h2{{color:#1565C0;font-size:17px;margin-bottom:12px;display:flex;align-items:center;gap:6px}}
    .box{{border-left:4px solid;border-radius:8px;padding:14px 16px;margin-top:10px;line-height:1.6}}
    .btn-wrap{{padding:25px;text-align:center;background:#F8FAFC}}
    .bot-btn{{display:inline-block;background:linear-gradient(135deg,#0088cc,#006699);color:#ffffff !important;
              text-decoration:none;padding:14px 28px;border-radius:30px;font-size:16px;font-weight:bold;
              box-shadow:0 4px 15px rgba(0,136,204,0.35);letter-spacing:.3px}}
    .ft{{background:#1E293B;color:#94A3B8;padding:16px 25px;text-align:center;font-size:13px;line-height:1.5}}
    p{{line-height:1.7;margin:4px 0;color:#334155}}
  </style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <h1>{g_emoji} ঢাকা ট্রান্সপোর্ট ও আবহাওয়া বুলেটিন</h1>
    <p>{greeting} | {now.strftime('%d/%m/%Y — %I:%M %p')}</p>
  </div>

  <div class="sec">
    <h2>🌡️ বর্তমান আবহাওয়া — ঢাকা</h2>
    {weather_html}
    <div class="box" style="background:{w_color};border-color:{w_border}">
      💡 <b>স্বাস্থ্য পরামর্শ:</b> {w_advice}
    </div>
  </div>

  <div class="sec">
    <h2>🚗 ট্রাফিক ও জ্যামের অবস্থা</h2>
    <p>বর্তমান পরিস্থিতি: <b>{jam['emoji']} {jam['level']}</b></p>
    <p>ব্যস্ত এলাকা: {areas}</p>
    <div class="box" style="background:{j_color};border-color:{j_border}">
      💡 <b>রাস্তার আপডেট:</b> {jam['advice']}
    </div>
  </div>

  <div class="sec">
    <h2>⏰ কখন বের হওয়া বুদ্ধিমানের কাজ?</h2>
    <div class="box" style="background:#E0F2FE;border-color:#0284C7;color:#0369A1">
      {depart}
    </div>
  </div>

  <!-- 🤖 সরাসরি টেলিগ্রাম বটের সাথে চ্যাট করার বাটন -->
  <div class="btn-wrap">
    <p style="font-size:15px;margin-bottom:14px;color:#1E293B;font-weight:600">
      কোথায় যাবেন বা কোন বাসে চড়বেন বুঝতে পারছেন না?
    </p>
    <a href="{TELEGRAM_BOT_URL}" target="_blank" class="bot-btn">
      💬 টেলিগ্রাম এআই এজেন্টের সাথে কথা বলুন
    </a>
    <p style="font-size:12px;color:#64748B;margin-top:10px">
      (ক্লিক করলেই সরাসরি টেলিগ্রাম বটে রুট ও পরামর্শ পেয়ে যাবেন)
    </p>
  </div>

  <div class="ft">
    🚌 ঢাকা ট্রান্সপোর্ট এআই প্ল্যাটফর্ম | স্বয়ংক্রিয় বুলেটিন<br>
    জরুরি পুলিশ ও ট্রাফিক সেবা পেতে কল করুন ৯৯৯-এ
  </div>
</div>
</body>
</html>"""


def send_alert_email() -> bool:
    now     = datetime.now()
    subject = f"🚌 ঢাকা ট্রাফিক ও আবহাওয়া আপডেট | {now.strftime('%d/%m/%Y %I:%M %p')}"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = GMAIL_ADDRESS
    msg['To']      = RECIPIENT_EMAIL
    msg.attach(MIMEText(_build_html(), 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_bytes())
        print(f"✅ ইমেইল পাঠানো হয়েছে [{now.strftime('%H:%M')}]")
        return True
    except Exception as e:
        print(f"❌ ইমেইল পাঠানো যায়নি: {e}")
        return False
