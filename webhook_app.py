import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
# Імпортуй сюди свої функції start, handle_callback тощо
from main import start, handle_callback  # заміни your_bot_module на ім'я файлу з ботом

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", "8443"))
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Встановлюємо вебхук автоматично при запуску
    await application.bot.set_webhook(WEBHOOK_URL)
    
    # Запускаємо webhook сервер
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    asyncio.run(main())
