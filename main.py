import asyncio
import os
import logging
from threading import Thread
from health_server import HealthServer
from keep_alive import start_keep_alive_background
from telegram.ext import Application, CommandHandler, MessageHandler, filters
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_health_server():
    """Ejecuta el health server en un hilo separado"""
    port = int(os.getenv('PORT', '5000'))
    health_server = HealthServer(port=port)
    asyncio.run(health_server.start_server())

async def main():
    """Inicializa y ejecuta el bot de Telegram"""
    # Inicia el health server en un hilo separado
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server started for UptimeRobot monitoring")

    # Inicia el servicio de keep-alive
    await start_keep_alive_background()

    # Configura el bot de Telegram
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Añade handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("confirmar_pago", confirmar_pago_handler))
    application.add_handler(CommandHandler("responder", responder_handler))

    # Comandos de respuesta rápida
    application.add_handler(CommandHandler("r", responder_rapido_handler))
    application.add_handler(CommandHandler("pendientes", pendientes_handler))
    application.add_handler(CommandHandler("ultima", ultima_pregunta_handler))
    application.add_handler(CommandHandler("rapida", respuesta_rapida_handler))
    application.add_handler(CommandHandler("admin", admin_status_handler))

    # Comandos numerados /r1, /r2, etc.
    for i in range(1, 10):
        application.add_handler(CommandHandler(f"r{i}", responder_numerado_handler))

    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Inicia el bot
    logger.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    
    # Configuración del polling
    await application.updater.start_polling(
        poll_interval=2.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=["message", "photo"]
    )
    
    # Mantiene el bot en ejecución
    await application.idle()

if __name__ == '__main__':
    asyncio.run(main())
