import asyncio
import logging
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
from keep_alive import start_keep_alive_background

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Initialize and start the Telegram bot with health server."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not configured. Please set it in environment variables.")
        return
    
    # Start health server for UptimeRobot monitoring
    health_server = HealthServer(port=5000)
    health_runner = await health_server.start_server()
    logger.info("Health server started for UptimeRobot monitoring")
    
    # Start internal keep-alive service (pings every 4 minutes)
    start_keep_alive_background()
    logger.info("Internal keep-alive service started")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("confirmar_pago", confirmar_pago_handler))
    application.add_handler(CommandHandler("responder", responder_handler))
    
    # Quick response commands
    application.add_handler(CommandHandler("r", responder_rapido_handler))
    application.add_handler(CommandHandler("pendientes", pendientes_handler))
    application.add_handler(CommandHandler("ultima", ultima_pregunta_handler))
    application.add_handler(CommandHandler("rapida", respuesta_rapida_handler))
    application.add_handler(CommandHandler("admin", admin_status_handler))
    
    # Numbered response commands /r1, /r2, /r3, etc.
    for i in range(1, 10):  # Support /r1 through /r9
        application.add_handler(CommandHandler(f"r{i}", responder_numerado_handler))
    
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Start the bot
    logger.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    
    # Start polling for updates with conflict handling
    updater = application.updater
    if updater:
        try:
            # Delete webhook first to avoid conflicts
            await application.bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)  # Wait for webhook deletion to propagate
            
            await updater.start_polling(
                poll_interval=2.0,
                timeout=30,
                drop_pending_updates=True,
                allowed_updates=["message", "photo"]
            )
            
            # Keep the bot running
            await asyncio.Event().wait()
        except Exception as e:
            logger.error(f"Error in bot polling: {e}")
        finally:
            try:
                await updater.stop()
                await application.stop()
                await application.shutdown()
                await health_runner.cleanup()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
    else:
        logger.error("Could not start updater")

if __name__ == '__main__':
    asyncio.run(main())
if __name__ == "__main__":
    from keep_alive import run_flask
    threading.Thread(target=run_flask, daemon=True).start()
    main()
