import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

import os
import asyncio
import logging
import threading
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
from health_server import HealthServer
from keep_alive import run_flask

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Start the full bot with menu, payments, admin commands and Render-ready port."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not configured. Please set it in environment variables.")
        return

    # Start Flask on port provided by Render (or fallback 5000)
    threading.Thread(
        target=run_flask,
        kwargs={'port': int(os.getenv("PORT", 5000))},
        daemon=True
    ).start()
    logger.info("Keep-alive Flask server started on port %s", os.getenv("PORT", 5000))

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add all handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("confirmar_pago", confirmar_pago_handler))
    application.add_handler(CommandHandler("responder", responder_handler))
    application.add_handler(CommandHandler("r", responder_rapido_handler))
    application.add_handler(CommandHandler("pendientes", pendientes_handler))
    application.add_handler(CommandHandler("ultima", ultima_pregunta_handler))
    application.add_handler(CommandHandler("rapida", respuesta_rapida_handler))
    application.add_handler(CommandHandler("admin", admin_status_handler))

    # Support /r1 … /r9 for quick admin replies
    for i in range(1, 10):
        application.add_handler(CommandHandler(f"r{i}", responder_numerado_handler))

    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()

    # Clean any webhook and start polling
    await application.bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)  # breve espera para propagar
    await application.updater.start_polling(
        poll_interval=2.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=["message", "photo"]
    )

    # Keep the bot alive
    await asyncio.Event().wait()

# ── Código final para Render ──
if __name__ == "__main__":
    import asyncio

    async def start_bot():
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        # Limpiar cualquier webhook o polling anterior
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.initialize()
        await app.start()
        # Iniciar polling limpio
        await app.updater.start_polling(drop_pending_updates=True)
        # Mantener el bot activo
        await asyncio.Event().wait()

    asyncio.run(start_bot())
