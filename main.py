import os
import logging
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import threading

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask додаток
app = Flask(__name__)

# Отримання токена
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    logger.error("TELEGRAM_BOT_TOKEN не встановлено!")
    exit(1)

# Створення бота та application
bot = Bot(token=token)
application = Application.builder().token(token).build()

# Отримання URL для webhook
base_url = os.getenv('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
if base_url.endswith('.'):
    base_url = base_url[:-1]
webhook_url = f"{base_url}/webhook/{token}"

# Змінні для зберігання стану
user_states = {}
user_data = {}

class UserState:
    NONE = 0
    WAITING_FOR_COMPANY = 1
    WAITING_FOR_CONTACT = 2
    WAITING_FOR_WORK_HOURS = 3
    WAITING_FOR_HOURLY_RATE = 4
    WAITING_FOR_DESCRIPTION = 5

# Обробники команд
async def start_command(update: Update, context):
    user_id = update.effective_user.id
    user_states[user_id] = UserState.NONE
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("📋 Створити рахунок", callback_data="create_invoice")],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 Привіт! Я бот для створення рахунків-фактур.

Я допоможу вам швидко створити професійний рахунок у форматі PDF.

Виберіть дію з меню нижче:
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context):
    help_text = """
🆘 Допомога по боту:

📋 Створення рахунку:
• Натисніть "Створити рахунок"
• Введіть дані крок за кроком
• Отримайте готовий PDF

💡 Корисні команди:
/start - Головне меню
/help - Ця довідка
/cancel - Скасувати операцію
    """
    await update.message.reply_text(help_text)

async def cancel_command(update: Update, context):
    user_id = update.effective_user.id
    user_states[user_id] = UserState.NONE
    user_data[user_id] = {}
    await update.message.reply_text("❌ Операцію скасовано. Напишіть /start для початку.")

# Обробка callback queries
async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "create_invoice":
        user_states[user_id] = UserState.WAITING_FOR_COMPANY
        user_data[user_id] = {}
        
        await query.edit_message_text(
            "📋 Створення рахунку\n\nКрок 1/5: Введіть назву вашої компанії:"
        )
        
    elif query.data == "about":
        about_text = """
ℹ️ Про бота:

Цей бот створений для швидкого формування рахунків-фактур у PDF форматі.

🔧 Функції:
• Створення професійних рахунків
• Експорт у PDF
• Підтримка української мови
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(about_text, reply_markup=reply_markup)
        
    elif query.data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("📋 Створити рахунок", callback_data="create_invoice")],
            [InlineKeyboardButton("ℹ️ Про бота", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 Привіт! Я бот для створення рахунків-фактур.

Я допоможу вам швидко створити професійний рахунок у форматі PDF.

Виберіть дію з меню нижче:
        """
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

# Обробка текстових повідомлень
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_states:
        user_states[user_id] = UserState.NONE
        user_data[user_id] = {}
    
    state = user_states[user_id]
    
    if state == UserState.WAITING_FOR_COMPANY:
        user_data[user_id]['company'] = text
        user_states[user_id] = UserState.WAITING_FOR_CONTACT
        
        await update.message.reply_text(
            "✅ Назву компанії збережено!\n\nКрок 2/5: Введіть контактну інформацію (телефон, email, адреса):"
        )
        
    elif state == UserState.WAITING_FOR_CONTACT:
        user_data[user_id]['contact'] = text
        user_states[user_id] = UserState.WAITING_FOR_WORK_HOURS
        
        await update.message.reply_text(
            "✅ Контактну інформацію збережено!\n\nКрок 3/5: Введіть кількість відпрацьованих годин:"
        )
        
    elif state == UserState.WAITING_FOR_WORK_HOURS:
        try:
            hours = float(text)
            if hours <= 0:
                raise ValueError("Години повинні бути більше 0")
                
            user_data[user_id]['hours'] = hours
            user_states[user_id] = UserState.WAITING_FOR_HOURLY_RATE
            
            await update.message.reply_text(
                "✅ Кількість годин збережено!\n\nКрок 4/5: Введіть погодинну ставку (у грн):"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Помилка! Введіть коректну кількість годин (наприклад: 8 або 8.5)"
            )
            
    elif state == UserState.WAITING_FOR_HOURLY_RATE:
        try:
            rate = float(text)
            if rate <= 0:
                raise ValueError("Ставка повинна бути більше 0")
                
            user_data[user_id]['rate'] = rate
            user_states[user_id] = UserState.WAITING_FOR_DESCRIPTION
            
            # Розрахунок загальної суми
            total = user_data[user_id]['hours'] * rate
            user_data[user_id]['total'] = total
            
            await update.message.reply_text(
                f"✅ Погодинну ставку збережено!\n\n"
                f"📊 Розрахунок:\n"
                f"• Години: {user_data[user_id]['hours']}\n"
                f"• Ставка: {rate} грн/год\n"
                f"• Загальна сума: {total:.2f} грн\n\n"
                f"Крок 5/5: Введіть опис робіт або напишіть 'готово':"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Помилка! Введіть коректну погодинну ставку (наприклад: 500 або 750.50)"
            )
            
    elif state == UserState.WAITING_FOR_DESCRIPTION:
        if text.lower() in ['готово', 'готов', 'готово!']:
            user_data[user_id]['description'] = "Надання IT послуг"
        else:
            user_data[user_id]['description'] = text
            
        # Створення PDF
        try:
            pdf_buffer = create_pdf_invoice(user_data[user_id])
            
            # Відправка PDF
            await context.bot.send_document(
                chat_id=user_id,
                document=pdf_buffer,
                filename=f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                caption="✅ Ваш рахунок готовий!"
            )
            
            # Скидання стану
            user_states[user_id] = UserState.NONE
            user_data[user_id] = {}
            
            # Повернення до головного меню
            keyboard = [[InlineKeyboardButton("📋 Створити новий рахунок", callback_data="create_invoice")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎉 Рахунок успішно створено!\n\nЩо бажаєте зробити далі?",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Помилка створення PDF: {e}")
            await update.message.reply_text(
                "❌ Помилка створення PDF. Спробуйте ще раз пізніше."
            )
            user_states[user_id] = UserState.NONE
            user_data[user_id] = {}
    else:
        # Стан не визначено
        await update.message.reply_text(
            "❓ Не розумію команду. Напишіть /start для початку роботи."
        )

def create_pdf_invoice(data):
    """Створення PDF рахунку"""
    buffer = io.BytesIO()
    
    # Створення PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Заголовок
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "RAHUNOK-FAKTURA")
    
    # Дата
    c.setFont("Helvetica", 12)
    current_date = datetime.now().strftime("%d.%m.%Y")
    c.drawString(50, height - 80, f"Data: {current_date}")
    
    # Інформація про компанію
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 120, "Postachalnik:")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 140, data['company'])
    
    # Контактна інформація
    lines = data['contact'].split('\n')
    y_pos = height - 160
    for line in lines:
        c.drawString(50, y_pos, line)
        y_pos -= 20
    
    # Опис робіт
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos - 40, "Opys robit:")
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y_pos - 60, data.get('description', 'Nadannia IT poslug'))
    c.drawString(50, y_pos - 80, f"Kilkist godyn: {data['hours']}")
    c.drawString(50, y_pos - 100, f"Pogodynna stavka: {data['rate']:.2f} grn")
    
    # Підсумок
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_pos - 140, f"ZAGALNA SUMA: {data['total']:.2f} grn")
    
    # Підпис
    c.setFont("Helvetica", 10)
    c.drawString(50, 50, "Diakuiemo za spivpratsiu!")
    
    c.save()
    buffer.seek(0)
    return buffer

# Додавання обробників до application
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("cancel", cancel_command))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Глобальні змінні для event loop
loop = None
loop_thread = None

def run_event_loop():
    """Запуск event loop в окремому потоці"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ensure_event_loop():
    """Переконуємося, що event loop запущений"""
    global loop, loop_thread
    if loop is None or not loop.is_running():
        loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        loop_thread.start()
        # Чекаємо, поки loop ініціалізується
        import time
        time.sleep(0.1)

# Flask маршрути
@app.route('/webhook/<token_path>', methods=['POST'])
def webhook(token_path):
    """Обробка webhook від Telegram"""
    if token_path != token:
        return "Unauthorized", 401
    
    try:
        # Переконуємося, що event loop запущений
        ensure_event_loop()
        
        # Отримання даних
        json_data = request.get_json()
        
        # Створення Update об'єкта
        update = Update.de_json(json_data, bot)
        
        # Обробка update в event loop
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            loop
        )
        # Чекаємо результат з таймаутом
        future.result(timeout=30)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Помилка webhook: {e}")
        return "Error", 500

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "active",
        "bot": "Telegram Invoice Bot",
        "webhook": webhook_url
    })

@app.route('/health')
def health():
    """Перевірка здоров'я"""
    return jsonify({"status": "healthy"})

async def setup_webhook():
    """Налаштування webhook"""
    try:
        # Видалення старого webhook
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        # Встановлення нового webhook
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook встановлено: {webhook_url}")
        print(f"✅ Webhook встановлено: {webhook_url}")
        
    except Exception as e:
        logger.error(f"Помилка встановлення webhook: {e}")
        print(f"❌ Помилка встановлення webhook: {e}")

def setup_webhook_sync():
    """Синхронне налаштування webhook"""
    asyncio.run(setup_webhook())

if __name__ == '__main__':
    # Налаштування webhook
    setup_webhook_sync()
    
    # Запуск Flask сервера
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
