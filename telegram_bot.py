from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat,
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
from email_sender import (
    add_subscriber, remove_subscriber, load_subscribers,
    trigger_welcome_email_async, get_last_delivery_event
)


import os
import json
import re
import html
from datetime import datetime

USERS_FILE = os.path.join(os.path.dirname(__file__), "bot_users.json")


def load_users() -> dict:
    """টেলিগ্রাম ব্যবহারকারীদের ডাটাবেজ লোড করা"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
    return {}


def save_users(users_dict: dict):
    """ব্যবহারকারীদের ডাটাবেজ সংরক্ষণ করা"""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")


def track_user(user):
    """প্রতিটি ব্যবহারকারীর আইডি, নাম ও শেষ সক্রিয় হওয়ার সময় স্বয়ংক্রিয়ভাবে ট্র্যাক করা"""
    if not user:
        return
    uid = str(user.id)
    users = load_users()
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "নামহীন"
    username = f"@{user.username}" if user.username else "নেই"

    if uid not in users:
        users[uid] = {
            "id": user.id,
            "name": full_name,
            "username": username,
            "first_seen": now_str,
            "last_seen": now_str,
            "msg_count": 1,
        }
    else:
        users[uid]["last_seen"] = now_str
        users[uid]["name"] = full_name
        users[uid]["username"] = username
        users[uid]["msg_count"] = users[uid].get("msg_count", 0) + 1

    save_users(users)


def get_start_button():
    """কথোপকথন শেষে বা শুরুতে ফ্রেশ স্টার্ট বাটন"""
    keyboard = [
        [InlineKeyboardButton("🚀 নতুন যাত্রা শুরু করুন (/start)", callback_data="btn_restart")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_active_buttons():
    """কথোপকথন চলাকালীন সহায়ক বাটন (মোবাইল ও পিসিতে ব্যালান্সড ও কাটার ঝুঁকিহীন)"""
    keyboard = [
        [
            InlineKeyboardButton("🚗 লাইভ জ্যাম", callback_data="btn_jam"),
            InlineKeyboardButton("🌡️ আবহাওয়া সতর্কতা", callback_data="btn_weather"),
        ],
        [
            InlineKeyboardButton("🔄 নতুন করে শুরু (/start)", callback_data="btn_restart"),
        ],
        [
            InlineKeyboardButton("✅ আমার কাজ শেষ / ধন্যবাদ", callback_data="btn_finish"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def notify_owner_new_subscriber(bot, user, email: str):
    """নতুন কেউ জিমেইল যোগ করলে সাথে সাথে Sahadat vai-কে টেলিগ্রামে নোটিফিকেশন দেওয়া"""
    if not user:
        return
    try:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "নামহীন"
        username = f"@{user.username}" if user.username else "নেই"
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        alert_msg = (
            "🔔 <b>নতুন জিমেইল সাবস্ক্রাইবার যুক্ত হয়েছে!</b>\n"
            "───────────────────────────\n"
            f"📧 <b>ইমেইল:</b> <code>{html.escape(email)}</code>\n"
            f"👤 <b>নাম:</b> {html.escape(full_name)}\n"
            f"🏷️ <b>ইউজারনেম:</b> {html.escape(username)}\n"
            f"🆔 <b>টেলিগ্রাম আইডি:</b> <code>{user.id}</code>\n"
            f"🕒 <b>সময়:</b> {now_str}\n"
            "───────────────────────────\n"
            "💡 সকল সাবস্ক্রাইবার দেখতে লিখুন: <code>/subscribers</code>"
        )
        await bot.send_message(chat_id=OWNER_TELEGRAM_ID, text=alert_msg, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending subscriber alert to owner: {e}")


# ─────────────────────────── /subscribe ───────────────────────
async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    args = ctx.args

    if not args:
        ctx.user_data["awaiting_email"] = True
        msg = (
            "📧 <b>ঢাকা ট্রাফিক ও আবহাওয়া দৈনিক ইমেইল বুলেটিন</b>\n"
            "───────────────────────────\n"
            "প্রতিদিন <b>সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায়</b> জিমেইলে ঢাকার রঙিন ট্রাফিক ও আবহাওয়া বুলেটিন পেতে:\n\n"
            "👉 <b>আপনার ইমেইল বা জিমেইল ঠিকানাটি সরাসরি নিচে লিখে মেসেজ দিন।</b>\n\n"
            "📌 <i>যেমন: rahim@gmail.com</i>\n\n"
            "💡 <i>(বাতিল করতে চাইলে /start লিখুন)</i>"
        )
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")
        return

    email = args[0].strip()
    success, reply_msg = add_subscriber(email, user_id)
    ctx.user_data["awaiting_email"] = False
    await update.message.reply_text(reply_msg)
    if success:
        await notify_owner_new_subscriber(ctx.bot, update.effective_user, email)


# ─────────────────────────── /unsubscribe ─────────────────────
async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    ctx.user_data["awaiting_email"] = False
    success, reply_msg = remove_subscriber(user_id)
    await update.message.reply_text(reply_msg)


# ─────────────────────────── /admin ───────────────────────────
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    if user_id != OWNER_TELEGRAM_ID:
        await update.message.reply_text(
            "⛔ <b>অ্যাক্সেস অস্বীকৃত!</b>\n\nএই বিশেষ অ্যাডমিন প্যানেলটি শুধুমাত্র বটের অফিসিয়াল প্রতিষ্ঠাতা ও ক্রিয়েটর Md Sahadat Hossain (Sahadat vai)-এর জন্য সংরক্ষিত।",
            parse_mode="HTML"
        )
        return

    knowledge = load_knowledge_base()
    learned_preview = ""
    if knowledge:
        learned_preview = "\n".join([f"• {html.escape(k.get('info', ''))} ({k.get('learned_at', '')})" for k in knowledge[-5:]])
    else:
        learned_preview = "• এখনো কোনো নতুন তথ্য জমা হয়নি।"

    subscribers = load_subscribers()
    sub_preview = ""
    if subscribers:
        sub_preview = "\n".join([f"  - {html.escape(s.get('email', ''))} ({s.get('subscribed_at', '')})" for s in subscribers[-5:]])
    else:
        sub_preview = "  - কোনো সাবস্ক্রাইবার এখনো নেই।"

    users = load_users()
    recent_users_text = ""
    for u in list(users.values())[-5:]:
        name_clean = html.escape(str(u.get('name', 'নামহীন')))
        uname_clean = html.escape(str(u.get('username', 'নেই')))
        recent_users_text += f"  - {name_clean} ({uname_clean}) | 🆔 <code>{u.get('id', '')}</code>\n"

    admin_text = (
        "👑 <b>অ্যাডমিন কন্ট্রোল সেন্টার | Dhaka Guide</b>\n"
        "───────────────────────────\n"
        f"• 👤 ক্রিয়েটর: <b>Md Sahadat Hossain</b>\n"
        f"• 🆔 টেলিগ্রাম আইডি: <code>{OWNER_TELEGRAM_ID}</code> (Verified ✅)\n"
        f"• 👥 <b>মোট টেলিগ্রাম ইউজার:</b> <b>{len(users)}</b> জন\n"
        f"• 📬 দৈনিক ইমেইল সাবস্ক্রাইবার: <b>{len(subscribers)}</b> জন\n"
        f"• 🧠 মানুষের থেকে শেখা তথ্য: <b>{len(knowledge)}</b> টি\n"
        f"• 💬 সক্রিয় ব্যবহারকারী সেশন: <b>{len(active_sessions)}</b> টি\n"
        "• 🧹 মেমোরি ক্লিনআপ: ৪৮ ঘণ্টা পর পর অটো-ক্লিন সক্রিয়\n"
        "• ☁️ ক্লাউড সার্ভার: Railway 24/7 Worker\n\n"
        f"👥 <b>সাম্প্রতিক টেলিগ্রাম ইউজারগণ:</b>\n{recent_users_text or '  - এখনো কোনো রেকর্ড নেই।'}\n"
        f"📬 <b>সাম্প্রতিক ইমেইল সাবস্ক্রাইবারগণ:</b>\n{sub_preview}\n\n"
        f"📚 <b>সাম্প্রতিক শেখা তথ্যের নমুনা:</b>\n{learned_preview}\n"
        "───────────────────────────\n"
        "💡 সব ইউজারের ডিটেইলস দেখতে: <code>/users</code>\n"
        "💡 সব সাবস্ক্রাইবারের ইমেইল তালিকা দেখতে: <code>/subscribers</code>"
    )
    await update.message.reply_text(admin_text, parse_mode="HTML")


# ─────────────────────────── /users ───────────────────────────
async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    if user_id != OWNER_TELEGRAM_ID:
        await update.message.reply_text("⛔ <b>অ্যাক্সেস অস্বীকৃত!</b>", parse_mode="HTML")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("ℹ️ এখনো কোনো ব্যবহারকারীর রেকর্ড নেই।")
        return

    lines = [f"👥 <b>বট ব্যবহারকারীদের পূর্ণাঙ্গ তালিকা (মোট: {len(users)} জন):</b>\n"]
    for i, u in enumerate(users.values(), 1):
        name_clean = html.escape(str(u.get('name', 'নামহীন')))
        uname_clean = html.escape(str(u.get('username', 'নেই')))
        lines.append(
            f"{i}. <b>{name_clean}</b> ({uname_clean})\n"
            f"   🆔 ID: <code>{u.get('id', '')}</code> | 💬 মেসেজ: {u.get('msg_count', 1)} বার\n"
            f"   🕒 প্রথম আগমন: {u.get('first_seen', 'N/A')}\n"
            f"   🕒 শেষ সক্রিয়: {u.get('last_seen', 'N/A')}\n"
        )

    msg = "\n".join(lines)
    if len(msg) > 4000:
        for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, parse_mode="HTML")


# ─────────────────────────── /subscribers ─────────────────────
async def cmd_subscribers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    if user_id != OWNER_TELEGRAM_ID:
        await update.message.reply_text("⛔ <b>অ্যাক্সেস অস্বীকৃত!</b>", parse_mode="HTML")
        return

    subscribers = load_subscribers()
    if not subscribers:
        await update.message.reply_text("ℹ️ এখনো কোনো জিমেইল সাবস্ক্রাইবার যুক্ত হয়নি।")
        return

    users = load_users()
    lines = [
        "📬 <b>জিমেইল বুলেটিন সাবস্ক্রাইবারদের পূর্ণাঙ্গ তালিকা:</b>\n"
        f"📊 <b>মোট সাবস্ক্রাইবার:</b> {len(subscribers)} জন\n"
        "───────────────────────────\n"
    ]
    for i, s in enumerate(subscribers, 1):
        email = html.escape(str(s.get('email', 'N/A')))
        sub_time = html.escape(str(s.get('subscribed_at', s.get('updated_at', 'N/A'))))
        chat_id = str(s.get('chat_id', 'N/A'))
        user_info = users.get(chat_id, {})
        user_name = html.escape(str(user_info.get('name', 'নামহীন')))
        username = html.escape(str(user_info.get('username', 'নেই')))
        
        lines.append(
            f"{i}. 📧 <code>{email}</code>\n"
            f"   👤 নাম: <b>{user_name}</b> ({username})\n"
            f"   🆔 Telegram ID: <code>{chat_id}</code>\n"
            f"   🕒 সাবস্ক্রাইব সময়: {sub_time}\n"
        )

    msg = "\n".join(lines)
    if len(msg) > 4000:
        for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, parse_mode="HTML")


# ─────────────────────────── /sendtest ────────────────────────
async def cmd_sendtest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    user_id = update.effective_user.id
    if user_id != OWNER_TELEGRAM_ID:
        await update.message.reply_text("⛔ <b>অ্যাক্সেস অস্বীকৃত!</b>", parse_mode="HTML")
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "💡 <b>যে কোনো ইমেইলে সরাসরি টেস্ট বুলেটিন পাঠাতে লিখুন:</b>\n"
            "<code>/sendtest target@gmail.com</code>",
            parse_mode="HTML"
        )
        return

    target_email = args[0].strip().lower()
    await update.message.reply_text(f"🚀 <code>{target_email}</code> ঠিকানায় ডুয়েল-পোর্ট ইঞ্জিনে লাইভ স্যাম্পল বুলেটিন পাঠানো হচ্ছে...")
    trigger_welcome_email_async(target_email)


# ─────────────────────────── /start ───────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
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
        f"• 🚗 ট্রাফিক: **{jam['level']}**\n"
        f"  ↳ 💡 *{jam['advice']}*\n"
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
    track_user(update.effective_user)
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

    if data == "btn_subscribe":
        ctx.user_data["awaiting_email"] = True
        msg = (
            "📧 <b>ঢাকা ট্রাফিক ও আবহাওয়া দৈনিক ইমেইল বুলেটিন</b>\n"
            "───────────────────────────\n"
            "প্রতিদিন <b>সকাল ০৭:০০, দুপুর ১২:০০ এবং সন্ধ্যা ০৬:০০ টায়</b> জিমেইলে ঢাকার রঙিন ট্রাফিক ও আবহাওয়া বুলেটিন পেতে:\n\n"
            "👉 <b>আপনার ইমেইল বা জিমেইল ঠিকানাটি সরাসরি নিচে লিখে মেসেজ দিন।</b>\n\n"
            "📌 <i>যেমন: rahim@gmail.com</i>\n\n"
            "💡 <i>(বাতিল করতে চাইলে /start লিখুন)</i>"
        )
        await query.message.reply_text(msg, parse_mode="HTML")
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
    track_user(update.effective_user)
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    
    # ১. ইউজার যদি ইমেইল দিয়ে সাবস্ক্রাইব করতে চায় (বা /subscribe চাপার পর অথবা মেসেজে সরাসরি ইমেইল লিখলে)
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if ctx.user_data.get("awaiting_email") or (email_match and len(text) < 120 and ("@" in text)):
        if email_match:
            email = email_match.group(0).strip()
            success, reply_msg = add_subscriber(email, user_id)
            ctx.user_data["awaiting_email"] = False
            await update.message.reply_text(reply_msg)
            if success:
                await notify_owner_new_subscriber(ctx.bot, update.effective_user, email)
            return
        elif ctx.user_data.get("awaiting_email"):
            await update.message.reply_text("⚠️ অনুগ্রহ করে একটি সঠিক ইমেইল এড্রেস লিখুন (যেমন: name@gmail.com) অথবা বাতিল করতে /start লিখুন।")
            return

    # ২. ইউজার যদি জিমেইল/ইমেইল না পাওয়ার অভিযোগ বা প্রশ্ন করে (যেমন: "amar gmaile to kono massage ashe ni")
    text_lower = text.lower()
    email_indicators = ["gmail", "email", "mail", "ইমেইল", "জিমেইল", "মেইল"]
    missing_indicators = [
        "ashe ni", "asheni", "paini", "pay nai", "আসেনি", "পাইনি", "পাচ্ছি না",
        "kothay", "কোথায়", "মেসেজ আসেনি", "massage ashe ni", "message ashe ni",
        "massage paini", "message paini", "pawa jay ni", "paowa jay ni"
    ]
    
    if any(ei in text_lower for ei in email_indicators) and any(mi in text_lower for mi in missing_indicators):
        subs = load_subscribers()
        user_email = None
        for s in subs:
            if s.get("chat_id") == user_id:
                user_email = s.get("email")
                break
        
        email_note = f"\n📧 আপনার সাবস্ক্রাইব করা ইমেইল: <code>{user_email}</code>\n" if user_email else ""
        help_msg = (
            "📬 <b>জিমেইল ইনবক্সে বুলেটিন দেখতে পাচ্ছেন না?</b>\n"
            "───────────────────────────\n"
            f"{email_note}\n"
            "ঘাবড়ানোর কিছু নেই! আমাদের সিস্টেম থেকে আপনার ইমেইল সফলভাবে পাঠানো হয়েছে। ইনবক্সে সরাসরি না পাওয়ার কারণ ও সহজ সমাধান:\n\n"
            "১. 📂 <b>Spam (স্প্যাম) ফোল্ডার চেক করুন:</b>\n"
            "যেহেতু নতুন কোনো সার্ভিস থেকে প্রথমবারের মতো অটোমেটেড ইমেইল পাঠানো হয়েছে, তাই গুগল সিকিউরিটির জন্য অনেক সময় তা ইনবক্সে না দিয়ে <b>Spam (স্প্যাম)</b> অথবা <b>Promotions / Updates</b> ফোল্ডারে রেখে দেয়।\n\n"
            "২. 📱 <b>মোবাইল জিমেইল অ্যাপে যেভাবে পাবেন:</b>\n"
            "• জিমেইল অ্যাপের উপরে বাঁদিকের <b>তিনটি দাগ (≡ Menu)</b> এ ক্লিক করুন।\n"
            "• নিচে নেমে <b>'Spam' (স্প্যাম)</b> অথবা <b>'All mail' (সকল মেইল)</b> ফোল্ডার ওপেন করুন।\n"
            "• সেখানে <b>'ঢাকা ট্রাফিক ও আবহাওয়া বুলেটিন'</b> দেখতে পাবেন।\n\n"
            "৩. ✅ <b>'Report Not Spam' এ ক্লিক করুন:</b>\n"
            "ইমেইলটি ওপেন করে <b>'Report not spam'</b> বা <b>'Move to Inbox'</b> দিন। তাহলে এরপর থেকে প্রতিদিনের ৩টি বুলেটিন সরাসরি আপনার প্রাইমারি ইনবক্সে চলে আসবে!\n\n"
            "💡 <i>আপনার সুবিধার জন্য আমরা এইমাত্র আপনার ঠিকানায় পুনরায় একটি লাইভ বুলেটিন পাঠিয়ে দিয়েছি! এখনই স্প্যাম ফোল্ডারটি চেক করে দেখুন।</i>"
        )
        if user_email:
            trigger_welcome_email_async(user_email)
        await update.message.reply_text(help_msg, parse_mode="HTML", reply_markup=get_active_buttons())
        return

    # ৩. Sahadat vai যদি জানতে চায় কেন ইমেইল বা কোনো প্রসেস ব্যর্থ হয়েছে
    if user_id == OWNER_TELEGRAM_ID:
        fail_queries = ["keno bertho", "bertho keno", "keno fail", "fail keno", "ব্যর্থ কেন", "ব্যর্থ হলো কেন", "কেন ব্যর্থ", "ব্যর্থতার কারণ", "ব্যর্থ হচ্ছে"]
        if any(fq in text_lower for fq in fail_queries):
            last_ev = get_last_delivery_event()
            recip = last_ev.get("recipient", "ব্যবহারকারীর ইমেইল")
            detail = last_ev.get("detail", "Railway আউটবাউন্ড SMTP পোর্ট 465/587 বন্ধ রেখেছে")
            exp_text = (
                f"👑 <b>Sahadat vai, <code>{recip}</code> ঠিকানায় ইমেইল ব্যর্থ হওয়ার আসল কারণ:</b>\n"
                "───────────────────────────\n"
                f"⚙️ <b>টেকনিক্যাল ত্রুটি:</b> <code>{html.escape(str(detail))}</code>\n\n"
                "🔍 <b>সহজ ভাষায় আসল কারণ:</b>\n"
                "আমাদের ক্লাউড সার্ভার (<b>Railway</b>) তাদের ফ্রি ও সাধারণ সার্ভারে আউটবাউন্ড সব SMTP পোর্ট (Port 465, 587, 25) কঠোরভাবে ব্লক করে রাখে (`Network is unreachable`), যাতে সার্ভার দিয়ে কোনো স্প্যাম ইমেইল ছড়ানো না যায়।\n\n"
                "💡 <b>সুসংবাদ ও তাৎক্ষণিক সমাধান:</b>\n"
                "১. ✅ আপনার পিসি থেকে সব পোর্ট ওপেন এবং আমি আপনার পিসি দিয়ে <code>mrhuraira2005@gmail.com</code>-এর জিমেইলে লাইভ বুলেটিন এইমাত্র সফলভাবে পাঠিয়ে দিয়েছি!\n"
                "২. 🌐 Railway ক্লাউড সার্ভার থেকে সবসময় ১০০% অটোমেটিক পাঠাতে হলে <b>HTTPS (Port 443)</b> মেথড ব্যবহার করতে হবে—যেমন একটি ফ্রি গুগল অ্যাপস স্ক্রিপ্ট বা Resend এপিআই যুক্ত করলেই রেলওয়ে ক্লাউড এটি আর কখনোই আটকাতে পারবে না।"
            )
            await update.message.reply_text(exp_text, parse_mode="HTML", reply_markup=get_active_buttons())
            return

    await update.message.chat.send_action(action="typing")
    res = get_ai_response(user_id, text)
    
    # যদি সেশন সম্পন্ন হয় তবে ফ্রেশ স্টার্ট বাটন দেখাবে
    markup = get_start_button() if res["is_complete"] else get_active_buttons()
    await update.message.reply_text(res["reply"], reply_markup=markup)


async def post_init(application: Application):
    """মেনুবারে পারসোনালাইজড বাটন সেট করা"""
    # ১. সাধারণ পাবলিক ইউজারদের মেনু (এখানে অ্যাডমিন সম্পূর্ণ গোপন থাকবে)
    public_commands = [
        BotCommand("start", "🚀 Start / Live Update"),
        BotCommand("subscribe", "📧 Subscribe Email"),
        BotCommand("unsubscribe", "❌ Unsubscribe"),
    ]
    await application.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())

    # ২. শুধুমাত্র আসল ক্রিয়েটর Sahadat vai-এর চ্যাটে সিক্রেট অ্যাডমিন শর্টকাট দেখাবে
    owner_commands = [
        BotCommand("start", "🚀 Start / Live Update"),
        BotCommand("subscribe", "📧 Subscribe Email"),
        BotCommand("unsubscribe", "❌ Unsubscribe"),
        BotCommand("admin", "👑 Admin Panel"),
        BotCommand("users", "👥 Users List"),
        BotCommand("subscribers", "📬 Subscribers List"),
        BotCommand("sendtest", "🧪 Test Email Dispatch"),
    ]
    try:
        await application.bot.set_my_commands(
            owner_commands,
            scope=BotCommandScopeChat(chat_id=OWNER_TELEGRAM_ID)
        )
    except Exception as e:
        print(f"Owner scoped commands notice: {e}")


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
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("subscribers", cmd_subscribers))
    app.add_handler(CommandHandler("emails", cmd_subscribers))
    app.add_handler(CommandHandler("sendtest", cmd_sendtest))
    app.add_handler(CommandHandler("testmail", cmd_sendtest))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("💬 Telegram পূর্ণাঙ্গ এআই এজেন্ট বট সফলভাবে চালু হয়েছে!")
    app.run_polling(drop_pending_updates=True)
