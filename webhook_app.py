import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, Dispatcher, filters
from telegram.ext import MessageHandler
from telegram.ext.webhook import Webhook

# Імпортуй сюди свої функції start, handle_callback тощо
from your_bot_module import start, handle_callback  # заміни your_bot_module на ім'я файлу з ботом

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", "8443"))

async def webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Тут передаємо оновлення до dispatcher
    dispatcher = context.application.dispatcher
    await dispatcher.process_update(update)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаємо сервер для прийому вебхука
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
