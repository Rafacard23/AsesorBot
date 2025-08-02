# main.py
import os
import asyncio
import logging

# Silenciar logs ruidosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

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
from keep_alive import run_flask
import threading

# Configurar logging propio
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

async def main() -> None:
    """Arranca el bot en Render: keep-alive + polling robusto."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN no está configurado.")
        return

    # 1. Keep-alive (Flask) en el puerto que asigna Render
    port = int(os.getenv("PORT", 5000))
    threading.Thread(
        target=run_flask,
        kwargs={"port": port},
        daemon=True,
    ).start()
    logger.info("Keep-alive Flask server iniciado en puerto %s", port)

    # 2. Crear la aplicación con mayor timeout para evitar Telegram TimedOut
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=15, read_timeout=15)
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .build()
    )

    # 3. Registrar handlers
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

    # 4. Inicializar, arrancar y polling
    await application.initialize()
    await application.start()
    # Eliminar webhook con re-intentos silenciosos
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning("No se pudo delete_webhook: %s", e)

    await application.updater.start_polling(
        poll_interval=2.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=["message", "photo"],
    )
    logger.info("Bot iniciado en polling mode")
    await asyncio.Event().wait()  # Mantener vivo

if __name__ == "__main__":
    asyncio.run(main())
