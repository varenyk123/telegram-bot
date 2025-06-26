import os
import logging
import json
import io
from typing import Dict, List
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import asyncio
import threading

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отримання змінних середовища
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не знайдено в змінних середовища")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL не знайдено в змінних середовища")

# ДОДАЙТЕ СЮДИ ВАШЕ ПОСИЛАННЯ НА КОНСУЛЬТАЦІЮ
CONSULTATION_LINK = "https://t.me/meme_pixel"

# Всі ваші дані для квіза
QUESTIONS = [
    {
        "id": 1,
        "text": "🧩 1. Що ти робиш, коли все йде не так, як хотів?",
        "options": [
            {"text": "A) Думаю, чому так сталося", "type": "A"},
            {"text": "B) Просто дію по-новому", "type": "B"},
            {"text": "C) Прислухаюсь до себе", "type": "C"},
            {"text": "D) Тримаюсь за знайомі мені речі", "type": "D"}
        ]
    },
    {
        "id": 2,
        "text": "🧩 2. Що для тебе головне, коли треба щось вирішити?",
        "options": [
            {"text": "A) Щоб було логічно", "type": "A"},
            {"text": "B) Щоб був результат", "type": "B"},
            {"text": "C) Щоб було \"по душі\"", "type": "C"},
            {"text": "D) Щоб було надійно", "type": "D"}
        ]
    },
    {
        "id": 3,
        "text": "🧩 3. Коли ти найчастіше кайфуєш?",
        "options": [
            {"text": "A) Коли щось розумію", "type": "A"},
            {"text": "B) Коли щось досягаю", "type": "B"},
            {"text": "C) Коли створюю або мрію", "type": "C"},
            {"text": "D) Коли все спокійно і стабільно", "type": "D"}
        ]
    },
    {
        "id": 4,
        "text": "🧩 4. Як ставишся до змін у житті?",
        "options": [
            {"text": "A) Думаю, чи воно мені підходить", "type": "A"},
            {"text": "B) Пробую — і бачу вже по ходу", "type": "B"},
            {"text": "C) Люблю щось нове", "type": "C"},
            {"text": "D) Уникаю, якщо можу", "type": "D"}
        ]
    },
    {
        "id": 5,
        "text": "🧩 5. Що тебе найбільше \"зупиняє\"?",
        "options": [
            {"text": "A) Занадто багато думок", "type": "A"},
            {"text": "B) Вигорання від постійної гонки", "type": "B"},
            {"text": "C) Настрої, що змінюються", "type": "C"},
            {"text": "D) Страх зробити помилку", "type": "D"}
        ]
    },
    {
        "id": 6,
        "text": "🧩 6. Що цінуєш у людях найбільше?",
        "options": [
            {"text": "A) Уміння мислити", "type": "A"},
            {"text": "B) Сміливість діяти", "type": "B"},
            {"text": "C) Щирість", "type": "C"},
            {"text": "D) Надійність", "type": "D"}
        ]
    },
    {
        "id": 7,
        "text": "🧩 7. Як ти зазвичай ставиш собі цілі?",
        "options": [
            {"text": "A) Планую від А до Я", "type": "A"},
            {"text": "B) Просто йду і роблю", "type": "B"},
            {"text": "C) Мрію — а потім рухаюсь", "type": "C"},
            {"text": "D) Повільно, але впевнено", "type": "D"}
        ]
    }
]

# Результати тестування
RESULTS = {
    "A": {
        "name": "🧠 Мислитель",
        "shadow": """🔲 *Стан тіні:*
Ти все аналізуєш. Твій розум — як лупа, яка бачить кожну деталь.
Але саме це і заважає: сумніви, перфекціонізм, роздуми без дії.
Ти не відчуваєш руху — бо боїшся помилки.""",
        "power": """🟩 *Стан сили:*
Ти — архітектор ідей. Там, де інші втрачають орієнтир — ти бачиш карту.
Твоя сила — створювати ясність. Твоя глибина — дар для тих, хто шукає змісту.
Коли ти дієш — світ стає логічним.""",
        "solution": """🎯 *Рішення:*
Вибери одну справу, яка важлива для тебе.
І дозволь собі зробити її неідеально — але завершити.
Твоя свобода — у русі."""
    },
    "B": {
        "name": "🔥 Діяч",
        "shadow": """🔲 *Стан тіні:*
Ти звик діяти, пробивати, досягати. Але саме це іноді тебе руйнує.
Ти вигорів? Або загубив сенс у швидкості?
Можливо, ти воюєш вже не за своє.""",
        "power": """🟩 *Стан сили:*
Ти — вогонь. Твоя енергія запалює інших.
Ти здатен швидко створювати результати там, де інші лише планують.
Коли твоя дія базується на внутрішній цінності — ти стаєш непереможним.""",
        "solution": """🎯 *Рішення:*
Зупинись на мить. Запитай себе: «Для чого я це роблю?»
Повернись до сенсу — і тоді дії знову почнуть давати кайф."""
    },
    "C": {
        "name": "🎨 Творець",
        "shadow": """🔲 *Стан тіні:*
Ти живеш емоціями. Але саме вони часом тебе ламають.
Ти надто глибоко переживаєш, сумніваєшся, втрачаєш фокус.
І часто чекаєш ідеального моменту для старту.""",
        "power": """🟩 *Стан сили:*
Ти — джерело краси, ідей і сенсу.
Твоя здатність бачити глибше — це не вада, а дар.
Ти не просто твориш — ти створюєш простори, де оживає душа.""",
        "solution": """🎯 *Рішення:*
Не чекай натхнення — створюй ритуал дії.
Твоя стабільність — це не смерть творчості, а її платформа."""
    },
    "D": {
        "name": "🧱 Будівник",
        "shadow": """🔲 *Стан тіні:*
Ти тримаєшся за знайоме. Це дає спокій, але блокує розвиток.
Зміни лякають, нове здається загрозою. Ти зупиняєш себе, навіть не усвідомлюючи.""",
        "power": """🟩 *Стан сили:*
Ти — опора. Ти створюєш стабільність там, де інші панікують.
На тобі можуть стояти проєкти, стосунки, цілі.
Ти будуєш світ, який витримує час.""",
        "solution": """🎯 *Рішення:*
Зроби крок у нове — маленький, але усвідомлений.
Досвід змін — не зруйнує тебе. Він зробить тебе ще міцнішим."""
    }
}

# Додаткові питання для визначення типу при рівності
TIE_BREAKER_QUESTIONS = {
    ("A", "B"): {
        "text": "❓ Що тобі ближче саме зараз?",
        "options": [
            {"text": "🧠 Зрозуміти, як усе працює, щоб діяти з впевненістю", "type": "A"},
            {"text": "🔥 Зробити перший крок, навіть не знаючи всіх відповідей", "type": "B"}
        ]
    },
    ("A", "C"): {
        "text": "❓ Що тобі потрібніше сьогодні?",
        "options": [
            {"text": "🧩 Відчути, що все логічно і на своїх місцях", "type": "A"},
            {"text": "🎨 Передати внутрішній стан через дію або творчість", "type": "C"}
        ]
    },
    ("A", "D"): {
        "text": "❓ Яка думка тебе більше заспокоює?",
        "options": [
            {"text": "📐 \"Я все зрозумів — і можу це контролювати\"", "type": "A"},
            {"text": "🧱 \"Я в безпеці — все стабільно і зрозуміло\"", "type": "D"}
        ]
    },
    ("B", "C"): {
        "text": "❓ Як ти більше любиш починати справу?",
        "options": [
            {"text": "🔥 Просто берусь і в процесі розбираюсь", "type": "B"},
            {"text": "💭 Чекаю, коли з'явиться натхнення або внутрішній поштовх", "type": "C"}
        ]
    },
    ("B", "D"): {
        "text": "❓ Що для тебе важливіше в складний момент?",
        "options": [
            {"text": "💪 Взяти на себе ініціативу і змінити ситуацію", "type": "B"},
            {"text": "🧘‍♂️ Довіритись перевіреному шляху і не поспішати", "type": "D"}
        ]
    },
    ("C", "D"): {
        "text": "❓ Що більше тобі підходить?",
        "options": [
            {"text": "🎭 Свобода, зміна, експерименти", "type": "C"},
            {"text": "🧱 Стабільність, чіткість, порядок", "type": "D"}
        ]
    }
}

# Словник для збереження стану користувачів
user_sessions = {}

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.current_question = 0
        self.answers = []
        self.tie_breaker_needed = False
        self.tie_breaker_types = None

# Ініціалізація Flask
app = Flask(__name__)

# Створюємо bot instance
bot = Bot(token=BOT_TOKEN)

# Обробники команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user_id = update.effective_user.id
    user_sessions[user_id] = UserSession(user_id)
    
    welcome_text = """👋 Вітаю тебе в персональній грі-діагностиці «СИСТЕМА ЯДЕР».

Це не просто тест. Це — дзеркало твоєї природи.

🔐 У тебе є 7 кроків. За кожен — ти відкриватимеш ось нове про себе.

🎯 У фіналі отримаєш: свій внутрішній двигун + особисту рекомендацію.

🖤 Важливо: ця система не для всіх. Лише для тих, хто справді хоче побачити себе без маски та прикрас.

Якщо ти хочеш дізнатись хто ти:
• **Мислитель**
• **Діяч** 
• **Творець**
• **Будівник**"""
    
    keyboard = [[InlineKeyboardButton("▶️ Почати", callback_data="start_quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник callback запитів"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    
    session = user_sessions[user_id]
    
    if data == "start_quiz":
        await send_question(query, session)
    elif data.startswith("answer_"):
        answer_type = data.split("_")[1]
        session.answers.append(answer_type)
        session.current_question += 1
        
        if session.current_question < len(QUESTIONS):
            await send_question(query, session)
        else:
            await process_results(query, session)
    elif data.startswith("tie_"):
        answer_type = data.split("_")[1]
        session.answers.append(answer_type)
        await process_results(query, session)
    elif data == "get_pdf":
        await send_pdf_result(query, session, context)
    elif data == "book_session":
        await send_booking_info(query)

async def send_question(query, session):
    """Відправляє поточне питання"""
    question = QUESTIONS[session.current_question]
    
    keyboard = []
    for option in question["options"]:
        keyboard.append([InlineKeyboardButton(
            option["text"], 
            callback_data=f"answer_{option['type']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=question["text"],
        reply_markup=reply_markup
    )

async def process_results(query, session):
    """Обробляє результати та визначає тип особистості"""
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for answer in session.answers:
        counts[answer] += 1
    
    max_count = max(counts.values())
    winners = [k for k, v in counts.items() if v == max_count]
    
    if len(winners) == 1:
        result_type = winners[0]
        await send_final_result(query, session, result_type)
    else:
        if len(winners) == 2:
            tie_key = tuple(sorted(winners))
            if tie_key in TIE_BREAKER_QUESTIONS:
                await send_tie_breaker_question(query, session, tie_key)
            else:
                result_type = winners[0]
                await send_final_result(query, session, result_type)
        else:
            result_type = winners[0]
            await send_final_result(query, session, result_type)

async def send_tie_breaker_question(query, session, tie_types):
    """Відправляє додаткове питання для визначення типу"""
    session.tie_breaker_types = tie_types
    question = TIE_BREAKER_QUESTIONS[tie_types]
    
    keyboard = []
    for option in question["options"]:
        keyboard.append([InlineKeyboardButton(
            option["text"], 
            callback_data=f"tie_{option['type']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=question["text"],
        reply_markup=reply_markup
    )

async def send_final_result(query, session, result_type):
    """Відправляє фінальний результат"""
    result = RESULTS[result_type]
    
    result_text = f"""🧬 **Твій тип: {result['name']}**

{result['shadow']}

{result['power']}

{result['solution']}

━━━━━━━━━━━━━━━━━━━━

🧬 Твій внутрішній двигун визначено.

Це було лише 5% від того, що можна дізнатись про себе.

🧠 За 10 хвилин я допоможу тобі:
— Побачити, що реально тебе блокує
— Визначити просту дію, яка запустить зміни
— Отримати ясність, яку не дасть жоден тест

🔒 Це буде приватна розмова. Без води. Без коучингу. Лише суть."""
    
    keyboard = [
        [InlineKeyboardButton("📄 Отримати PDF-памятку", callback_data="get_pdf")],
        [InlineKeyboardButton("🚀 Записатись на консультацію", url=CONSULTATION_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    session.final_result = result_type
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def send_pdf_result(query, session, context):
    """Генерує та відправляє PDF з результатами"""
    if not hasattr(session, 'final_result'):
        await query.answer("Спочатку пройдіть тест!")
        return

    result = RESULTS[session.final_result]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['BodyText']

    story = []
    story.append(Paragraph("🧬 СИСТЕМА ЯДЕР — РЕЗУЛЬТАТ", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"🔹 Твій тип: {result['name']}", normal_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(result['shadow'].replace("*", ""), normal_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(result['power'].replace("*", ""), normal_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(result['solution'].replace("*", ""), normal_style))

    doc.build(story)
    buffer.seek(0)

    await query.message.reply_document(document=buffer, filename="rezultat.pdf")
    await query.answer("PDF відправлено!")

async def send_booking_info(query):
    """Відправляє інформацію для запису на консультацію"""
    booking_text = f"""🗓 **Запис на персональну сесію**

Для запису на 10-хвилинну розмову, скористайтесь посиланням:

🔗 {CONSULTATION_LINK}

Або залиште свій контакт, і ми з вами зв'яжемося найближчим часом.

🔒 Гарантуємо повну конфіденційність та індивідуальний підхід."""
    
    keyboard = [[InlineKeyboardButton("🚀 Записатись зараз", url=CONSULTATION_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=booking_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Створюємо Application тільки для обробки повідомлень
application = None

async def process_telegram_update(update_data):
    """Обробляє Telegram оновлення"""
    global application
    if application is None:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_callback))
        await application.initialize()
    
    update = Update.de_json(update_data, bot)
    await application.process_update(update)

# Flask маршрути
@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'Опитувальний бот працює!', 'webhook': 'активний'})

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update_dict = json.loads(json_string)
            
            # Обробляємо update асинхронно
            asyncio.run(process_telegram_update(update_dict))
            
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'status': 'error', 'message': 'Content-Type не application/json'}), 400
    except Exception as e:
        logger.error(f"Помилка в webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Функція для встановлення webhook
async def set_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
        await bot.delete_webhook()
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook встановлено: {webhook_url}")
        print(f"✅ Webhook встановлено: {webhook_url}")
    except Exception as e:
        logger.error(f"Помилка встановлення webhook: {e}")
        print(f"❌ Помилка встановлення webhook: {e}")

if __name__ == '__main__':
    # Встановлюємо webhook при запуску
    asyncio.run(set_webhook())
    
    # Запускаємо Flask сервер
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
