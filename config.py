import os
import base64

# ========================================
# ঢাকা ট্রান্সপোর্ট বট — কনফিগারেশন
# ========================================

def _dec(b_str: str) -> str:
    try:
        return base64.b64decode(b_str).decode("utf-8")
    except Exception:
        return ""

GMAIL_ADDRESS       = os.environ.get("GMAIL_ADDRESS", _dec("c2FoYWRhdC5pbmZvMDFAZ21haWwuY29t"))
GMAIL_APP_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", _dec("ZGVpemJ0bndncXBhd3Z2dQ=="))
RECIPIENT_EMAIL     = os.environ.get("RECIPIENT_EMAIL", _dec("c2FoYWRhdC5pbmZvMDFAZ21haWwuY29t"))

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", _dec("YzlmZDlkNGJkYWQzYmVkZjJiMWZhYzU2NDgzMDlhNGI="))
DHAKA_CITY          = "Dhaka,BD"

TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", _dec("ODg5NDE0MTg3NTpBQUZ6MkxqVmN2SE5Mczk2Tk9Da1VqbHlRcnhiaTdldDlNcw=="))
GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", _dec("QVEuQWI4Uk42Sm1LOGU5eGVyTm9ZMUtRdEoxM2cwWjl6WW5nRmFZcS1ZTElCdFVpdmVyUlE="))

ALERT_TIMES = ["07:00", "12:00", "18:00"]

# 👑 ক্রিয়েটর ও অ্যাডমিনের ভেরিফাইড টেলিগ্রাম আইডি
OWNER_TELEGRAM_ID = int(os.environ.get("OWNER_TELEGRAM_ID", "7042555228"))

# 🌐 ক্লাউড সার্ভার (Railway) থেকে সরাসরি ইমেইল পাঠানোর HTTPS রিলে
GOOGLE_SCRIPT_URL   = os.environ.get("GOOGLE_SCRIPT_URL", _dec("aHR0cHM6Ly9zY3JpcHQuZ29vZ2xlLmNvbS9tYWNyb3Mvcy9BS2Z5Y2J6bWt1WG53MU9kbF9uLTNPNGtaTXRlb3NvbmQ4N2prSTB3YnlWSjBCRVNEQkRDRW14WDZvUHNRN2FLOTl1RE11cXlJZy9leGVj")).strip()
RESEND_API_KEY      = os.environ.get("RESEND_API_KEY", "").strip()
