import os
import logging
import json
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import io

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Замініть на ваш токен від BotFather
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Дані для квіза
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
        await send_pdf_result(query, session)
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
    # Підраховуємо відповіді
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for answer in session.answers:
        counts[answer] += 1
    
    # Знаходимо максимальну кількість
    max_count = max(counts.values())
    winners = [k for k, v in counts.items() if v == max_count]
    
    if len(winners) == 1:
        # Є явний переможець
        result_type = winners[0]
        await send_final_result(query, session, result_type)
    else:
        # Потрібне додаткове питання
        if len(winners) == 2:
            tie_key = tuple(sorted(winners))
            if tie_key in TIE_BREAKER_QUESTIONS:
                await send_tie_breaker_question(query, session, tie_key)
            else:
                # Якщо немає додаткового питання, вибираємо перший варіант
                result_type = winners[0]
                await send_final_result(query, session, result_type)
        else:
            # Більше 2 варіантів з однаковою кількістю - вибираємо перший
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
        [InlineKeyboardButton("🚀 Записатись на 10-хвилинну розмову", callback_data="book_session")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Зберігаємо результат в сесії
    session.final_result = result_type
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def send_pdf_result(query, session):
    """Генерує та відправляє PDF з результатами"""
    if not hasattr(session, 'final_result'):
        await query.answer("Спочатку пройдіть тест!")
        return
    
    result = RESULTS[session.final_result]
    
    # Створюємо PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Стилі
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    # Контент
    story = []
    
    # Заголовок
    story.append(Paragraph("Система ЯДЕР - Результати", title_style))
    story.append(Spacer(1, 12))
    
    # Результат
    story.append(Paragraph(f"Твій тип: {result['name']}", title_style))
    story.append(Spacer(1, 12))
    
    # Додаємо текст результатів (очищений від markdown)
    shadow_text = result['shadow'].replace('*', '').replace('🔲', '').replace('🟩', '').replace('🎯', '')
    power_text = result['power'].replace('*', '').replace('🔲', '').replace('🟩', '').replace('🎯', '')
    solution_text = result['solution'].replace('*', '').replace('🔲', '').replace('🟩', '').replace('🎯', '')
    
    story.append(Paragraph("Стан тіні:", styles['Heading2']))
    story.append(Paragraph(shadow_text, normal_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Стан сили:", styles['Heading2']))
    story.append(Paragraph(power_text, normal_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Рішення:", styles['Heading2']))
    story.append(Paragraph(solution_text, normal_style))
    
    # Будуємо PDF
    doc.build(story)
    buffer.seek(0)
    
    # Відправляємо файл
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=buffer,
        filename=f"sistema_yader_{result['name'].replace('🧠 ', '').replace('🔥 ', '').replace('🎨 ', '').replace('🧱 ', '').lower()}.pdf",
        caption="📄 Ваші результати тестування"
    )
    
    await query.answer("PDF відправлено!")

async def send_booking_info(query):
    """Відправляє інформацію для запису на консультацію"""
    booking_text = """🗓 **Запис на персональну сесію**

Для запису на 10-хвилинну розмову, будь ласка, напишіть особисто:

📱 Telegram: @meme_pixel

Або залиште свій контакт, і ми з вами зв'яжемося найближчим часом.

🔒 Гарантуємо повну конфіденційність та індивідуальний підхід."""
    
    await query.edit_message_text(
        text=booking_text,
        parse_mode='Markdown'
    )

def main():
    """Головна функція"""
    # Створюємо додаток
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Додаємо обробники
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаємо бота
    application.run_polling()

if __name__ == '__main__':
    main()
