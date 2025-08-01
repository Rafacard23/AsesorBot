import os
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading

# --- Variables de entorno ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_CHAT_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
BANCO = os.getenv("BANCO", "Banco Ejemplo")
CEDULA = os.getenv("CEDULA_IDENTIDAD", "V00000000")
TELEFONO = os.getenv("NUMERO_TELEFONO", "00000000000")
TASA_BCV = float(os.getenv("TASA_BCV", "119.40").replace(",", "."))  # ← Acepta coma o punto

# --- Flask dummy para Render ---
app = Flask(__name__)

@app.route("/")
def health():
    return {"status": "Bot is alive", "tasa": TASA_BCV}, 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- Arrancar Flask en segundo plano ---
threading.Thread(target=run_flask, daemon=True).start()

# --- Bot de Telegram ---
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"¡Hola! Estoy listo.\n"
        f"Tasa BCV: {TASA_BCV:.2f} Bs/USD"
    )
    await update.message.reply_text(text)

def main():
    if not TOKEN:
        raise RuntimeError("Falta la variable de entorno TELEGRAM_TOKEN")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    main()
