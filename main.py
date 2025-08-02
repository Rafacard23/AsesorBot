# main.py  – Versión webhook para Render (24/7)
import os
import asyncio
import logging

# Silenciar logs ruidosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from handlers import (
    start_handler,
    message_handler,
    photo_handler,
    confirmar_pago_handler,
    responder_handler,
    responder_rapido_handler,
    pendientes_handler,
    ultima_pregunta_handler,
    responder_numerado_handler,
    respuesta_rapida_handler,
    admin_status_handler
)
from telegram.request import HTTPXRequest

# Logging propio
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# 1. Crear la aplicación de Telegram
# -------------------------------------------------
request = HTTPXRequest(connect_timeout=15, read_timeout=15)
application = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .request(request)
    .build()
)

# -------------------------------------------------
# 2. Registrar todos los handlers
# -------------------------------------------------
application.add_handler(CommandHandler("start", start_handler))
application.add_handler(CommandHandler("confirmar_pago", confirmar_pago_handler))
application.add_handler(CommandHandler("responder", responder_handler))
application.add_handler(CommandHandler("r", responder_rapido_handler))
application.add_handler(CommandHandler("pendientes", pendientes_handler))
application.add_handler(CommandHandler("ultima", ultima_pregunta_handler))
application.add_handler(CommandHandler("rapida", respuesta_rapida_handler))
application.add_handler(CommandHandler("admin", admin_status_handler))
for i in range(1, 10):
    application.add_handler(CommandHandler(f"r{i}", responder_numerado_handler))
application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# -------------------------------------------------
# 3. Flask app para webhook y keep-alive
# -------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def ping():
    return "Bot alive", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_data = request.get_data().decode()
        update = Update.de_json(json_data, application.bot)
        asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            application.bot.loop
        )
        return "", 200
    abort(403)

# -------------------------------------------------
# 4. Inicializar y setear webhook al arrancar
# -------------------------------------------------
async def set_webhook():
    url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(url, drop_pending_updates=True)
    logger.info("Webhook configurado en %s", url)

if __name__ == "__main__":
    # Preparar la app
    asyncio.run(set_webhook())
    # Arrancar Flask (Gunicorn se encargará en producción)
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
