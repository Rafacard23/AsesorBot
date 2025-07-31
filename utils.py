import asyncio
import logging
import uuid
import os
import datetime
from telegram import ReplyKeyboardMarkup
from config import TIEMPO_SESION_EXTENDIDA_MINUTOS, TIPO_SESION_EXTENDIDA

logger = logging.getLogger(__name__)

# Global storage for user data
pagos_pendientes = {}
conversaciones_usuarios = {}
ultimo_usuario_pregunta = None  # Store last user who asked a question
preguntas_pendientes = {}  # Store pending questions with timestamps
user_last_interaction = {}  # Track last interaction time to detect returning users

async def finalizar_sesion_estandar(context, chat_id):
    """Send message to client indicating that standard session has ended."""
    if chat_id not in conversaciones_usuarios:
        return
    
    nombre_usuario = conversaciones_usuarios[chat_id]['nombre_usuario']
    keyboard = [
        ['⭐ Sesión Estándar (2$)'],
        ['💎 Sesión Extendida (4$)'],
        ['🏠 Volver al Menú Principal']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    mensaje = (
        f"¡Tu sesión estándar ha finalizado, {nombre_usuario}! 🎉\n\n"
        "Espero haber resuelto tu consulta.\n\n"
        "Si necesitas seguir conversando o tienes nuevas preguntas, "
        "puedes elegir continuar con otra sesión:"
    )
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            reply_markup=reply_markup
        )
        # Mark session as finished
        conversaciones_usuarios[chat_id]['estado'] = 'finalizada'
        logger.info(f"Standard session finished for {chat_id}.")
    except Exception as e:
        logger.error(f"Error sending standard session finish message to {chat_id}: {e}")

async def iniciar_temporizador_extendida(context, chat_id):
    """Start a 20-minute timer for extended session."""
    await asyncio.sleep(TIEMPO_SESION_EXTENDIDA_MINUTOS * 60)
    
    if chat_id in conversaciones_usuarios and conversaciones_usuarios[chat_id].get('tipo_sesion') == TIPO_SESION_EXTENDIDA:
        nombre_usuario = conversaciones_usuarios[chat_id]['nombre_usuario']
        keyboard = [
            ['⭐ Sesión Estándar (2$)'],
            ['💎 Sesión Extendida (4$)'],
            ['🏠 Volver al Menú Principal']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        mensaje = (
            f"⏰ ¡Tiempo cumplido, {nombre_usuario}!\n\n"
            "Tu sesión extendida de 20 minutos ha finalizado.\n\n"
            "¿Deseas continuar con otra sesión? Puedes elegir:"
        )
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje,
                reply_markup=reply_markup
            )
            conversaciones_usuarios[chat_id]['estado'] = 'expirada_extendida'
            logger.info(f"Extended session expired for {chat_id}.")
        except Exception as e:
            logger.error(f"Error expiring extended session for {chat_id}: {e}")

def generate_service_keyboard():
    """Generate the main service selection keyboard."""
    return [['🚀 Coach Motivacional', '💙 Apoyo Emocional'], ['📚 Ayuda para Docentes']]

def generate_session_keyboard():
    """Generate session type selection keyboard."""
    return [
        ['⭐ Sesión Estándar (2$)'],
        ['💎 Sesión Extendida (4$)'],
        ['🏠 Volver al Menú Principal']
    ]

def generate_main_menu_keyboard():
    """Generate main menu keyboard."""
    return [
        ['🚀 Coach Motivacional', '💙 Apoyo Emocional'],
        ['📚 Ayuda para Docentes']
    ]

def save_temp_file(file_data, extension='.jpg'):
    """Save temporary file and return the path."""
    temp_file_path = f"temp_verification_{uuid.uuid4()}{extension}"
    with open(temp_file_path, 'wb') as f:
        f.write(file_data)
    return temp_file_path

def cleanup_temp_file(file_path):
    """Remove temporary file if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Temporary file {file_path} removed.")
    except Exception as e:
        logger.error(f"Error removing temporary file {file_path}: {e}")

def is_returning_user(chat_id, current_time):
    """
    Detect if user is returning to chat after being away.
    Returns True if user hasn't interacted in the last 2 minutes.
    """
    if chat_id not in user_last_interaction:
        return False
    
    last_interaction = user_last_interaction[chat_id]
    time_diff = (current_time - last_interaction).total_seconds()
    
    # Consider user as returning if they haven't interacted for more than 2 minutes
    return time_diff > 120

def should_show_welcome_menu(chat_id):
    """
    Determine if we should show a welcome menu to returning user.
    Returns False if user is in states where buttons shouldn't appear.
    """
    # Don't show menu if user has pending payment (waiting for payment proof)
    if chat_id in pagos_pendientes:
        pago_info = pagos_pendientes[chat_id]
        # If they haven't completed payment process, don't show menu
        if 'tipo_sesion_elegida' in pago_info and 'servicio' in pago_info:
            return False
    
    # Don't show menu if user has active conversation
    if chat_id in conversaciones_usuarios:
        sesion = conversaciones_usuarios[chat_id]
        if sesion.get('estado') == 'activa':
            return False
    
    return True

def get_appropriate_keyboard_for_user(chat_id):
    """
    Get the appropriate keyboard based on user's current state.
    """
    # Check if user has finished session and should see session options
    if chat_id in conversaciones_usuarios:
        sesion = conversaciones_usuarios[chat_id]
        if sesion.get('estado') in ['finalizada', 'expirada_extendida']:
            return generate_session_keyboard()
    
    # Check if user has selected service but not session type
    if chat_id in pagos_pendientes:
        pago_info = pagos_pendientes[chat_id]
        if 'servicio' in pago_info and 'tipo_sesion_elegida' not in pago_info:
            return generate_session_keyboard()
    
    # Default to main service menu
    return generate_service_keyboard()

async def handle_returning_user(update, context):
    """
    Handle returning user by showing appropriate menu if needed.
    Returns True if handled, False if normal message processing should continue.
    """
    if not update.effective_user or not update.message:
        return False
    
    chat_id = update.message.chat.id
    current_time = datetime.datetime.now()
    
    # Skip for admin
    from config import YOUR_TELEGRAM_ID
    if chat_id == YOUR_TELEGRAM_ID:
        return False
    
    # Check if this is a returning user first
    is_returning = is_returning_user(chat_id, current_time)
    
    # Update interaction time (after checking if returning)
    user_last_interaction[chat_id] = current_time
    
    # If not returning user, don't show welcome menu
    if not is_returning:
        return False
    
    # Check if we should show welcome menu
    if not should_show_welcome_menu(chat_id):
        return False
    
    # Get appropriate keyboard and show welcome message
    keyboard = get_appropriate_keyboard_for_user(chat_id)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    nombre_usuario = update.effective_user.first_name or "Usuario"
    
    # Determine welcome message based on user state
    if chat_id in conversaciones_usuarios:
        sesion = conversaciones_usuarios[chat_id]
        if sesion.get('estado') in ['finalizada', 'expirada_extendida']:
            mensaje = f"¡Hola de nuevo, {nombre_usuario}! ¿Te gustaría iniciar una nueva sesión?"
        else:
            mensaje = f"¡Bienvenido de vuelta, {nombre_usuario}! ¿En qué puedo ayudarte?"
    else:
        mensaje = f"¡Hola de nuevo, {nombre_usuario}! ¿En qué puedo ayudarte hoy?"
    
    await update.message.reply_text(mensaje, reply_markup=reply_markup)
    logger.info(f"Returning user {chat_id} welcomed back with appropriate menu")
    
    return True
