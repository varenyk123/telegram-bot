import os
from telegram import Bot

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

bot = Bot(token=BOT_TOKEN)

def set_webhook():
    success = bot.set_webhook(WEBHOOK_URL)
    if success:
        print(f"Webhook успішно встановлено на {WEBHOOK_URL}")
    else:
        print("Не вдалося встановити webhook")

if __name__ == "__main__":
    set_webhook()
