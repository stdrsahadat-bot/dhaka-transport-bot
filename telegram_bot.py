from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)
from telegram.request import HTTPXRequest
from config import TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID
from jam_analyzer import get_jam_status
from weather import get_dhaka_weather
from ai_agent import get_ai_response, clear_history, load_knowledge_base, active_sessions


def get_start_button():
    """কথোপকথন শেষে বা শুরুতে ফ্রেশ স্টার্ট বাটন"""
    keyboard = [
        [InlineKeyboardButton("🚀 নতুন যাত্রা শুরু করুন (/start)", callback_data="btn_restart")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_active_buttons():
    """কথোপকথন চলাকালীন সহায়ক বাটন"""
    keyboard = [
        [
            InlineKeyboardButton("🚗 লাইভ জ্যাম পরিস্থিতি", callback_data="btn_jam"),
            InlineKeyboardButton("🌡️ আবহাওয়া সতর্কতা", callback_data="btn_weather"),
        ],
        [
            InlineKeyboardButton("✅ আমার কাজ শেষ / ধন্যবাদ", callback_data="btn_finish"),
            InlineKeyboardButton("🔄 নতুন করে শুরু", callback_data="btn_restart"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ─────────────────────────── /admin ───────────────────────────
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_TELEGRAM_ID:
        await update.message.reply_text(
            "⛔ **অ্যাক্সেস অস্বীকৃত!**\n\nএই বিশেষ অ্যাডমিন প্যানেলটি শুধুমাত্র বটের অফিসিয়াল প্রতিষ্ঠাতা ও ক্রিয়েটর Md Sahadat Hossain (Sahadat vai)-এর জন্য সংরক্ষিত।"
        )
        return

    knowledge = load_knowledge_base()
    learned_preview = ""
    if knowledge:
        learned_preview = "\n".join([f"• {k['info']} ({k['learned_at']})" for k in knowledge[-5:]])
    else:
        learned_preview = "• এখনো কোনো নতুন তথ্য জমা হয়নি।"

    admin_text = (
        "👑 **অ্যাডমিন কন্ট্রোল সেন্টার | Dhaka Guide**\n"
        "───────────────────────────\n"
        f"• 👤 ক্রিয়েটর: **Md Sahadat Hossain**\n"
        f"• 🆔 টেলিগ্রাম আইডি: `{OWNER_TELEGRAM_ID}` (Verified ✅)\n"
        f"• 🧠 মানুষের থেকে শেখা তথ্য: **{len(knowledge)}** টি\n"
        f"• 👥 সক্রিয় ব্যবহারকারী সেশন: **{len(active_sessions)}** টি\n"
        "• 🧹 মেমোরি ক্লিনআপ: ৪৮ ঘণ্টা পর পর অটো-ক্লিন সক্রিয়\n"
        "• ☁️ ক্লাউড সার্ভার: Railway 24/7 Worker\n\n"
        f"📚 **সাম্প্রতিক শেখা তথ্যের নমুনা:**\n{learned_preview}\n"
        "───────────────────────────\n"
        "বট পুরোপুরি নিরাপদ ও সুস্থভাবে চলছে! 🟢"
    )
    await update.message.reply_text(admin_text)


# ─────────────────────────── /start ───────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_history(user_id)

    # বর্তমান আবহাওয়া ও ট্রাফিক লাইভ ডাটা
    jam = get_jam_status()
    w = get_dhaka_weather()
    
    temp_str = f"{w['temp']}°C" if w else "স্বাভাবিক"
    rain_str = f"বৃষ্টির সম্ভাবনা: {w['rain_chance']}%" if w else ""
    
    if user_id == OWNER_TELEGRAM_ID:
        greeting_header = (
            "👑 **আস্সালামু আলাইকুম Sahadat vai!**\n"
            "ঢাকা ট্রান্সপোর্ট এআই এজেন্টে স্বাগতম। আপনি আমার ভেরিফাইড ক্রিয়েটর ও অ্যাডমিন। 🇧🇩\n"
        )
    else:
        greeting_header = (
            "🚌 **আস্সালামু আলাইকুম!**\n"
            "ঢাকা ট্রান্সপোর্ট এআই এজেন্টে আপনাকে স্বাগতম। 🇧🇩\n"
        )

    welcome_text = (
        f"{greeting_header}\n"
        f"📊 **বর্তমান ঢাকার অবস্থা:**\n"
        f"• 🚗 ট্রাফিক: **{jam['level']}** ({jam['advice']})\n"
        f"• 🌡️ আবহাওয়া: **{temp_str}** {rain_str}\n\n"
        "──────────────────────\n"
        "💬 **আপনি এখন ঠিক কোথা থেকে কোথায় যাবেন?**\n"
        "শুধু জায়গার নাম দুটি লিখে জানান (যেমন: *'ফার্মগেট থেকে মিরপুর'* বা *'উত্তরা যাবো'*), আমি সেরা রুট, বাস/মেট্রো ও ন্যায্য ভাড়া হিসাব করে দিচ্ছি!"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_active_buttons(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, reply_markup=get_active_buttons(), parse_mode="Markdown")


# ─────────────────── বাটনে ক্লিকের হ্যান্ডলার ───────────────────
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "btn_restart":
        await cmd_start(update, ctx)
        return

    if data == "btn_finish":
        clear_history(user_id)
        finish_text = (
            "💚 **ঢাকা গাইড থেকে সেবা নেওয়ার জন্য আপনাকে অসংখ্য ধন্যবাদ!**\n\n"
            "আপনার পথচলা নিরাপদ, স্বস্তিদায়ক ও সুন্দর হোক। রাস্তায় কোনো প্রয়োজন হলে আবার চলে আসবেন!\n\n"
            "শুভ যাত্রা! 🌟"
        )
        await query.message.reply_text(finish_text, reply_markup=get_start_button(), parse_mode="Markdown")
        return

    await query.message.chat.send_action(action="typing")

    prompt_map = {
        "btn_jam": "বর্তমান ঢাকা শহরের ট্রাফিক ও জ্যামের সার্বিক অবস্থা মাত্র ২ লাইনে বুলেট পয়েন্টে বলো।",
        "btn_weather": "বর্তমান আবহাওয়া অনুযায়ী রাস্তায় বের হলে কী সতর্কতা নেওয়া উচিত তা অতি সংক্ষেপে ২ লাইনে বলো।",
    }

    user_intent = prompt_map.get(data, "যাতায়াত সংক্রান্ত তথ্য দিন।")
    res = get_ai_response(user_id, user_intent)
    
    markup = get_start_button() if res["is_complete"] else get_active_buttons()
    await query.message.reply_text(res["reply"], reply_markup=markup)


# ─────────────────── টেক্সট মেসেজ হ্যান্ডলার ───────────────────
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.effective_user.id
    
    await update.message.chat.send_action(action="typing")
    res = get_ai_response(user_id, text)
    
    # যদি সেশন সম্পন্ন হয় তবে ফ্রেশ স্টার্ট বাটন দেখাবে
    markup = get_start_button() if res["is_complete"] else get_active_buttons()
    await update.message.reply_text(res["reply"], reply_markup=markup)


async def post_init(application: Application):
    """মেনুবারে স্থায়ী বাটন সেট করা"""
    commands = [
        BotCommand("start", "শুরু করুন / বর্তমান ঢাকা আপডেট"),
        BotCommand("admin", "অ্যাডমিন প্যানেল (Sahadat vai)"),
    ]
    await application.bot.set_my_commands(commands)


# ──────────────────────── রান বট ────────────────────────────
def run_telegram_bot():
    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
    )

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("💬 Telegram পূর্ণাঙ্গ এআই এজেন্ট বট সফলভাবে চালু হয়েছে!")
    app.run_polling(drop_pending_updates=True)
