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
from health_server import HealthServer  # ¡Mantén esta línea!  
from keep_alive import start_keep_alive_background  

# Configure logging  
logging.basicConfig(  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  
    level=logging.INFO  
)  

logger = logging.getLogger(__name__)  

def run_health_server():  
    """Ejecuta el health server en un hilo separado"""  
    health_server = HealthServer(host="localhost", port=5000)    
    asyncio.run(health_server.start_server())  

async def main():  
    """Inicializa y ejecuta el bot de Telegram"""  
    if not TELEGRAM_TOKEN:  
        logger.error("TELEGRAM_TOKEN is not configured. Please set it in environment variables.")  
        return  

    # Inicia el health server en un hilo SEPARADO  
    threading.Thread(target=run_health_server, daemon=True).start()  
    logger.info("Health server started for UptimeRobot monitoring")  

    # Inicia el servicio de keep-alive  
    await start_keep_alive_background()   
    logger.info("Internal keep-alive service started")  

    # Crea la aplicación de Telegram  
    application = Application.builder().token(TELEGRAM_TOKEN).build()  

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
    updater = application.updater  
    if updater:  
        try:  
            await application.bot.delete_webhook(drop_pending_updates=True)  
            await asyncio.sleep(2)  

            await updater.start_polling(  
                poll_interval=2.0,  
                timeout=30,  
                drop_pending_updates=True,  
                allowed_updates=["message", "photo"]  
            )  

            await asyncio.Event().wait()  # Mantiene el bot en ejecución  
        except Exception as e:  
            logger.error(f"Error in bot polling: {e}")  
        finally:  
            try:  
                await updater.stop()  
                await application.stop()  
                await application.shutdown()  
            except Exception as e:  
                logger.error(f"Error during shutdown: {e}")  
    else:  
        logger.error("Could not start updater")  

if __name__ == '__main__':  
    asyncio.run(main())  
