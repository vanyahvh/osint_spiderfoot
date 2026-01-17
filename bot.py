import os
import requests
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from weasyprint import HTML

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

# ---------- CONFIG ----------
TOR_ENABLED = False
TOR_PROXY = "socks5h://127.0.0.1:9050"

GITHUB_RAW_FILES = [
    "https://raw.githubusercontent.com/vanyok1337/osint-db/main/emails.txt",
    "https://raw.githubusercontent.com/vanyok1337/osint-db/main/fio.txt"
]
# ----------------------------


def session():
    s = requests.Session()
    if TOR_ENABLED:
        s.proxies.update({"http": TOR_PROXY, "https": TOR_PROXY})
    s.headers.update({"User-Agent": "SpiderFoot-Light"})
    return s


def dorks(q):
    q = q.replace(" ", "+")
    return f"""🔎 Google Dorks

https://www.google.com/search?q="{q}"
https://www.google.com/search?q=site:github.com+"{q}"
https://www.google.com/search?q=site:pastebin.com+"{q}"
https://www.google.com/search?q=site:reddit.com+"{q}"

"""


def github_docs_search(query):
    s = session()
    found = []

    for url in GITHUB_RAW_FILES:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            continue
        for line in r.text.splitlines():
            if query.lower() in line.lower():
                found.append(f"{url}\n{line}")

    if not found:
        return "📂 GitHub Docs: совпадений нет\n\n"

    return "📂 GitHub Docs:\n" + "\n".join(found) + "\n\n"


def email_osint(email):
    return f"""📧 EMAIL OSINT

Email: {email}

🧪 holehe (локально):
holehe {email}

🔎 GHunt:
https://github.com/mxrch/GHunt

{dorks(email)}
{github_docs_search(email)}
"""


def fio_osint(fio):
    q = fio.replace(" ", "+")
    return f"""👤 FIO OSINT

ФИО: {fio}

📰 СМИ:
https://www.google.com/search?q="{q}"

⚖ Судебные решения:
https://reyestr.court.gov.ua/search?text={q}

🗂 Aleph:
https://aleph.occrp.org/search?q={q}

{github_docs_search(fio)}
"""


def github_osint(username):
    r = session().get(f"https://api.github.com/users/{username}")
    if r.status_code != 200:
        return "❌ GitHub пользователь не найден"

    u = r.json()
    return f"""🧑‍💻 GITHUB OSINT

Username: {username}
Name: {u.get("name")}
Bio: {u.get("bio")}
Location: {u.get("location")}
Repos: {u.get("public_repos")}
Followers: {u.get("followers")}

{u.get("html_url")}
"""


def ip_osint(ip):
    r = session().get(f"https://ipinfo.io/{ip}/json")
    if r.status_code != 200:
        return "❌ IP недоступен"

    d = r.json()
    return f"""🌐 IP OSINT

IP: {ip}
Country: {d.get("country")}
City: {d.get("city")}
Org: {d.get("org")}
Location: {d.get("loc")}
Timezone: {d.get("timezone")}
"""


def export_pdf(content):
    name = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    html = f"<html><meta charset='utf-8'><pre>{content}</pre></html>"
    HTML(string=html).write_pdf(name)
    return name


# -------- TELEGRAM --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📧 Email", callback_data="email")],
        [InlineKeyboardButton("👤 FIO", callback_data="fio")],
        [InlineKeyboardButton("🧑‍💻 GitHub", callback_data="github")],
        [InlineKeyboardButton("🌐 IP", callback_data="ip")],
    ]
    await update.message.reply_text(
        "🕵️ SpiderFoot‑light\nВыбери тип поиска:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data
    await q.edit_message_text("✏ Введи данные для поиска")


async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text.strip()

    if not mode:
        await update.message.reply_text("Нажми /start")
        return

    if mode == "email":
        report = email_osint(text)
    elif mode == "fio":
        report = fio_osint(text)
    elif mode == "github":
        report = github_osint(text)
    elif mode == "ip":
        report = ip_osint(text)
    else:
        report = "Ошибка"

    context.user_data["report"] = report

    kb = [[InlineKeyboardButton("📄 PDF", callback_data="pdf")]]
    await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(kb))


async def pdf_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    report = context.user_data.get("report")
    if not report:
        return

    pdf = export_pdf(report)
    await q.message.reply_document(open(pdf, "rb"))
    os.remove(pdf)


app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(choose, pattern="^(email|fio|github|ip)$"))
app.add_handler(CallbackQueryHandler(pdf_cb, pattern="^pdf$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))
app.run_polling()
