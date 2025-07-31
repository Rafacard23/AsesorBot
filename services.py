import logging
from telegram.constants import ParseMode
from config import YOUR_TELEGRAM_ID

logger = logging.getLogger(__name__)

async def notify_admin_user_question(context, chat_id, nombre_usuario, pregunta):
    """Notify admin about user question in active session."""
    if not YOUR_TELEGRAM_ID:
        logger.error("YOUR_TELEGRAM_ID not configured. Cannot notify admin.")
        return
    
    # Store as last user who asked a question for /r command
    import utils
    utils.ultimo_usuario_pregunta = chat_id
    
    # Store in pending questions with timestamp
    import datetime
    utils.preguntas_pendientes[chat_id] = {
        'nombre': nombre_usuario,
        'pregunta': pregunta,
        'timestamp': datetime.datetime.now()
    }
    
    try:
        # Format for easy copy-paste to ChatGPT
        consulta_formateada = f'"{nombre_usuario}: {pregunta}"'
        
        mensaje_admin = (
            f"**📝 Nueva Pregunta de Usuario**\n\n"
            f"👤 **{nombre_usuario}** (ID: `{chat_id}`)\n\n"
            f"💬 **Consulta para ChatGPT:**\n"
            f"`{consulta_formateada}`\n\n"
            f"⚡ **Responder rápido:** `/r [tu_respuesta]`\n"
            f"📋 **Ver pendientes:** `/pendientes`\n"
            f"🔄 **Última pregunta:** `/ultima`"
        )
        
        await context.bot.send_message(
            chat_id=YOUR_TELEGRAM_ID,
            text=mensaje_admin,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"User question notification sent to admin for {chat_id}")
        
    except Exception as e:
        logger.error(f"Error sending user question notification: {e}")

def format_service_name(servicio):
    """Format service name for display."""
    service_names = {
        'coach_motivacional': 'Coach Motivacional',
        'apoyo_emocional': 'Apoyo Emocional',
        'ayuda_docentes': 'Ayuda para Docentes'
    }
    return service_names.get(servicio, servicio)

def format_session_name(tipo_sesion):
    """Format session type name for display."""
    session_names = {
        'sesion_estandar': 'Sesión Estándar',
        'sesion_extendida': 'Sesión Extendida'
    }


    
