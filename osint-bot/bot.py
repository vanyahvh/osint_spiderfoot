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

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

HEADERS = {"User-Agent": "AuthorOSINTBot/1.0"}
TIMEOUT = 15
# ==========================


def req(url):
    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except:
        return None


# ---------- AUTHOR DORK ENGINE ----------

def dorks(query):
    q = query.replace(" ", "+")
    return f"""
🔎 AUTHOR DORK ENGINE

• Google:
https://www.google.com/search?q="{q}"

• GitHub code:
https://www.google.com/search?q=site:github.com+"{q}"

• Documents:
https://www.google.com/search?q=filetype:pdf+"{q}"
https://www.google.com/search?q=filetype:doc+"{q}"

• Forums:
https://www.google.com/search?q=site:reddit.com+"{q}"
https://www.google.com/search?q=site:forum+"{q}"

• Archives:
https://web.archive.org/cite/{q}
"""


# ---------- MODULES ----------

def email_osint(email):
    return f"""
📧 EMAIL OSINT

Target: {email}

• Email reputation:
https://emailrep.io/{email}

• Breach check (manual):
https://haveibeenpwned.com/

• Gravatar:
https://www.gravatar.com/{email}

• Username correlation:
https://www.google.com/search?q="{email}"

{dorks(email)}
"""


def username_osint(username):
    return f"""
👤 USERNAME OSINT

Target: {username}

• Social presence:
https://whatsmyname.app/?q={username}

• GitHub:
https://github.com/{username}

• GitLab:
https://gitlab.com/{username}

• Keybase:
https://keybase.io/{username}

• Search:
https://www.google.com/search?q="{username}"

{dorks(username)}
"""


def github_osint(user):
    r = req(f"https://api.github.com/users/{user}")
    if not r or r.status_code != 200:
        return "❌ GitHub user not found"

    u = r.json()
    return f"""
🧑‍💻 GITHUB OSINT

Username: {u.get("login")}
Name: {u.get("name")}
Bio: {u.get("bio")}
Company: {u.get("company")}
Location: {u.get("location")}
Public repos: {u.get("public_repos")}
Followers: {u.get("followers")}
Following: {u.get("following")}

Profile:
{u.get("html_url")}
"""


def ip_osint(ip):
    r = req(f"https://ipinfo.io/{ip}/json")
    if not r or r.status_code != 200:
        return "❌ IP lookup failed"

    d = r.json()
    return f"""
🌐 IP OSINT

IP: {ip}
Country: {d.get("country")}
Region: {d.get("region")}
City: {d.get("city")}
Org: {d.get("org")}
Location: {d.get("loc")}
Timezone: {d.get("timezone")}

• Abuse reports:
https://www.abuseipdb.com/check/{ip}
"""


def phone_osint(phone):
    return f"""
📱 PHONE OSINT (LIMITED)

Target: {phone}

• Google search:
https://www.google.com/search?q="{phone}"

• Scam reports:
https://www.google.com/search?q="{phone}"+scam

• Public mentions:
https://web.archive.org/cite/{phone}

⚠ No private databases used.
"""


# ---------- TELEGRAM ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📧 Email", callback_data="email")],
        [InlineKeyboardButton("👤 Username", callback_data="username")],
        [InlineKeyboardButton("🧑‍💻 GitHub", callback_data="github")],
        [InlineKeyboardButton("🌐 IP", callback_data="ip")],
        [InlineKeyboardButton("📱 Phone", callback_data="phone")]
    ]
    await update.message.reply_text(
        "🕵️ Author OSINT Bot\nSelect search module:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data
    await q.edit_message_text("✏ Send target")


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text.strip()

    if not mode:
        await update.message.reply_text("Use /start")
        return

    if mode == "email":
        res = email_osint(text)
    elif mode == "username":
        res = username_osint(text)
    elif mode == "github":
        res = github_osint(text)
    elif mode == "ip":
        res = ip_osint(text)
    elif mode == "phone":
        res = phone_osint(text)
    else:
        res = "Error"

    await update.message.reply_text(res)


# ---------- RUN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(choose))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

app.run_polling()
