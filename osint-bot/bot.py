import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from supabase import create_client

# ========== ENV ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not set")

# ========== SUPABASE ==========
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET = "osint-files"

FILES_BY_TYPE = {
    "email": ["emails.txt", "mixed.txt"],
    "username": ["usernames.txt", "mixed.txt"],
    "phone": ["phones.txt", "mixed.txt"],
    "ip": ["ips.txt", "mixed.txt"],
}

HEADERS = {"User-Agent": "AuthorOSINTBot/1.0"}
TIMEOUT = 15


# ========== CLOUD FILE SEARCH ==========
def search_in_files(query, mode, limit=10):
    query = query.lower()
    results = []

    files = FILES_BY_TYPE.get(mode, [])
    for fname in files:
        try:
            url = supabase.storage.from_(BUCKET).get_public_url(fname)
            r = requests.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                continue

            for line in r.text.splitlines():
                if query in line.lower():
                    results.append(f"[{fname}] {line}")
                    if len(results) >= limit:
                        return results
        except Exception as e:
            print("Search error:", e)

    return results


# ========== OSINT MODULES ==========
def dorks(q):
    q = q.replace(" ", "+")
    return f"""
🔎 Dorks
https://www.google.com/search?q="{q}"
https://www.google.com/search?q=site:github.com+"{q}"
https://www.google.com/search?q=filetype:pdf+"{q}"
"""


def email_osint(email):
    return f"""
📧 EMAIL OSINT
Target: {email}

• EmailRep:
https://emailrep.io/{email}

• Gravatar:
https://www.gravatar.com/{email}

{dorks(email)}
"""


def username_osint(username):
    return f"""
👤 USERNAME OSINT
Target: {username}

• WhatsMyName:
https://whatsmyname.app/?q={username}

• GitHub:
https://github.com/{username}

{dorks(username)}
"""


def phone_osint(phone):
    return f"""
📱 PHONE OSINT
Target: {phone}

• Google:
https://www.google.com/search?q="{phone}"

• Scam reports:
https://www.google.com/search?q="{phone}"+scam
"""


def ip_osint(ip):
    r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=TIMEOUT)
    if r.status_code != 200:
        return "❌ IP lookup failed"

    d = r.json()
    return f"""
🌐 IP OSINT
IP: {ip}
Country: {d.get("country")}
City: {d.get("city")}
Org: {d.get("org")}
Location: {d.get("loc")}

• AbuseIPDB:
https://www.abuseipdb.com/check/{ip}
"""


# ========== TELEGRAM ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📧 Email", callback_data="email")],
        [InlineKeyboardButton("👤 Username", callback_data="username")],
        [InlineKeyboardButton("📱 Phone", callback_data="phone")],
        [InlineKeyboardButton("🌐 IP", callback_data="ip")]
    ]
    await update.message.reply_text(
        "🕵️ Author OSINT Bot\nВыбери тип поиска:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data
    await q.edit_message_text("✏ Введи запрос")


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text.strip()

    if not mode:
        await update.message.reply_text("Нажми /start")
        return

    if mode == "email":
        res = email_osint(text)
    elif mode == "username":
        res = username_osint(text)
    elif mode == "phone":
        res = phone_osint(text)
    elif mode == "ip":
        res = ip_osint(text)
    else:
        res = "Ошибка"

    matches = search_in_files(text, mode)

    if matches:
        res += "\n\n📂 Cloud DB matches:\n"
        for m in matches:
            res += f"• {m}\n"
    else:
        res += "\n\n📂 Cloud DB: no matches"

    await update.message.reply_text(res)


# ========== RUN ==========
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(choose))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

print("Bot started")
app.run_polling()
