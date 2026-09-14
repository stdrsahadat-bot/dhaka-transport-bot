import os

# ========================================
# ঢাকা ট্রান্সপোর্ট বট — কনফিগারেশন
# (সব API Key .env ফাইলে বা Render Environment Variables থেকে আসবে)
# ========================================

GMAIL_ADDRESS       = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL     = os.environ.get("RECIPIENT_EMAIL", "")

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
DHAKA_CITY          = "Dhaka,BD"

TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")

ALERT_TIMES = ["07:00", "12:00", "18:00"]
