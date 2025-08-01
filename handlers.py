import asyncio
import logging
import uuid
import datetime
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import (
    YOUR_TELEGRAM_ID, NUMERO_TELEFONO, CEDULA_IDENTIDAD, BANCO, TASA_BCV,
    MENU_OPCIONES_A_TIPO, PRECIO_SESION, MENU_SERVICIOS_A_TIPO,
    TIPO_SESION_ESTANDAR, TIPO_SESION_EXTENDIDA
)
import utils
from utils import (
    pagos_pendientes, conversaciones_usuarios, preguntas_pendientes,
    generate_service_keyboard, generate_session_keyboard, generate_main_menu_keyboard,
    finalizar_sesion_estandar, iniciar_temporizador_extendida,
    save_temp_file, cleanup_temp_file
)
from services import notify_admin_user_question, format_service_name, format_session_name

logger = logging.getLogger(__name__)

# Diccionario con los resúmenes empáticos para cada servicio
RESUMEN_SERVICIOS = {
    'coach_motivacional': '🚀 Te acompañaré en tu camino hacia el éxito personal y profesional. Juntos identificaremos tus metas, superaremos obstáculos y desbloquearemos todo tu potencial. Cada paso que des será un avance hacia la mejor versión de ti mismo.',
    'apoyo_emocional': '💙 Estoy aquí para brindarte un espacio seguro donde puedas expresarte libremente. Te ofrezco comprensión, herramientas de bienestar emocional y el acompañamiento que necesitas para encontrar tu equilibrio interior, además descubrir mensajes valiosos de tus sueños pues no son casualidad, sino avisos ocultos de tu alma.',
    'ayuda_docentes': '📚 Como educador, mereces todo el apoyo para brillar en tu noble labor. Te ayudaré con estrategias pedagógicas innovadoras, manejo del aula y herramientas para potenciar el aprendizaje de tus estudiantes.'
}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not update.effective_user or not update.message:
        return

    nombre = update.effective_user.first_name or "Usuario"
    keyboard = generate_service_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"¡Hola {nombre}! 🌟 Bienvenido a Apoyo Integral. Estoy aquí para acompañarte en tu camino de crecimiento y bienestar ¿En qué puedo ayudarte hoy? Elige una opción del menú y comencemos juntos.",
        reply_markup=reply_markup
    )
    logger.info(f"User {nombre} (ID: {update.message.chat.id}) started the bot.")

async def mostrar_informacion_pago(update: Update, context: ContextTypes.DEFAULT_TYPE, tipo_sesion_elegida: str, precio_dolares: float):
    """Show payment information and save pending request."""
    chat_id_usuario = update.message.chat.id

    if not all([NUMERO_TELEFONO, CEDULA_IDENTIDAD, BANCO, TASA_BCV]):
        await update.message.reply_text(
            "Error en la configuración del bot. Los datos de pago no están completos. Por favor, contacta al administrador."
        )
        logger.error("Missing payment data or BCV rate in configuration.")
        return

    precio_bolivares = precio_dolares * TASA_BCV
    tipo_sesion_formateada = format_session_name(tipo_sesion_elegida)

    mensaje = (
        f"Para la {tipo_sesion_formateada} ({precio_dolares}$), el monto a pagar es de *{precio_bolivares:.2f} bolívares*.\n\n"
        f"Datos para el pago móvil:\n"
        f"📱 Número de teléfono: *{NUMERO_TELEFONO}*\n"
        f"🆔 Cédula de identidad: *{CEDULA_IDENTIDAD}*\n"
        f"🏦 Banco: *{BANCO}*\n\n"
        f"Por favor, envía el comprobante de pago con la referencia para confirmar tu sesión."
    )

    await update.message.reply_text(
        mensaje,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Payment information shown for {tipo_sesion_formateada}.")

    # Save pending payment info
    pagos_pendientes[chat_id_usuario] = {
        'tipo_sesion_elegida': tipo_sesion_elegida,
        'precio_dolares': precio_dolares,
        'nombre_usuario': update.message.from_user.first_name
    }
    logger.info(f"Pending payment info saved for {chat_id_usuario}: {pagos_pendientes[chat_id_usuario]}")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo receipt verification."""
    if not YOUR_TELEGRAM_ID or YOUR_TELEGRAM_ID == 1234567890:
        logger.error("YOUR_TELEGRAM_ID is not configured. Cannot send payment notifications.")
        await update.message.reply_text(
            "Error en la configuración del bot. No se pueden enviar notificaciones de pago."
        )
        return

    try:
        chat_id_usuario = update.message.chat.id
        nombre_usuario = update.message.from_user.first_name

        if chat_id_usuario not in pagos_pendientes:
            await update.message.reply_text(
                "Por favor, primero selecciona un servicio y tipo de sesión antes de enviar el comprobante."
            )
            logger.warning(f"Receipt received from {chat_id_usuario} without pending payment info.")
            return

        info_pago_usuario = pagos_pendientes[chat_id_usuario]
        tipo_sesion_elegida = info_pago_usuario['tipo_sesion_elegida']
        precio_dolares = info_pago_usuario['precio_dolares']

        # Download the photo
        photo_file = await update.message.photo[-1].get_file()
        file_data = await photo_file.download_as_bytearray()
        temp_file_path = save_temp_file(file_data)

        # Send to admin with payment info and clickable command
        caption_mensaje_admin = (
            f"**🔔 Nuevo Comprobante de Pago Pendiente**\n"
            f"De: {nombre_usuario} (ID: `{chat_id_usuario}`)\n"
            f"Servicio: {format_session_name(tipo_sesion_elegida)}\n"
            f"Monto (USD): {precio_dolares}\n\n"
            f"--- Para confirmar y activar la sesión IA, envía tu comando: ---\n"
            f"`/confirmar_pago {chat_id_usuario} {tipo_sesion_elegida}`"
        )

        with open(temp_file_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=YOUR_TELEGRAM_ID,
                photo=photo,
                caption=caption_mensaje_admin,
                parse_mode=ParseMode.MARKDOWN
            )

        await update.message.reply_text(
            "¡Comprobante de pago recibido! Gracias por tu paciencia mientras lo verificamos."
        )
        logger.info(f"Payment receipt received from {chat_id_usuario} and forwarded to {YOUR_TELEGRAM_ID}.")

        # Cleanup temporary file
        cleanup_temp_file(temp_file_path)

    except Exception as e:
        logger.error(f"Error handling photo for verification: {e}")
        await update.message.reply_text(
            "Ocurrió un error al procesar tu comprobante. Por favor, inténtalo de nuevo más tarde."
        )

async def handle_text_payment_reference(update: Update, context: ContextTypes.DEFAULT_TYPE, referencia: str):
    """Handle payment reference sent as text."""
    if not YOUR_TELEGRAM_ID or YOUR_TELEGRAM_ID == 1234567890:
        logger.error("YOUR_TELEGRAM_ID is not configured. Cannot send payment notifications.")
        await update.message.reply_text(
            "Error en la configuración del bot. No se pueden enviar notificaciones de pago."
        )
        return

    try:
        chat_id_usuario = update.message.chat.id
        nombre_usuario = update.message.from_user.first_name or "Usuario"

        if chat_id_usuario not in pagos_pendientes:
            await update.message.reply_text(
                "Por favor, primero selecciona un servicio y tipo de sesión antes de enviar la referencia."
            )
            logger.warning(f"Payment reference received from {chat_id_usuario} without pending payment info.")
            return

        info_pago_usuario = pagos_pendientes[chat_id_usuario]
        tipo_sesion_elegida = info_pago_usuario['tipo_sesion_elegida']
        precio_dolares = info_pago_usuario['precio_dolares']

        # Send to admin with payment info and clickable command
        mensaje_admin = (
            f"**🔔 Nueva Referencia de Pago (TEXTO)**\n"
            f"De: {nombre_usuario} (ID: `{chat_id_usuario}`)\n"
            f"Servicio: {format_session_name(tipo_sesion_elegida)}\n"
            f"Monto (USD): {precio_dolares}\n"
            f"Referencia: `{referencia}`\n\n"
            f"--- Para confirmar y activar la sesión, envía: ---\n"
            f"`/confirmar_pago {chat_id_usuario} {tipo_sesion_elegida}`"
        )

        await context.bot.send_message(
            chat_id=YOUR_TELEGRAM_ID,
            text=mensaje_admin,
            parse_mode=ParseMode.MARKDOWN
        )

        await update.message.reply_text(
            "¡Referencia de pago recibida! Gracias por tu paciencia mientras verificamos el pago."
        )
        logger.info(f"Payment reference received from {chat_id_usuario} and forwarded to {YOUR_TELEGRAM_ID}: {referencia}")

    except Exception as e:
        logger.error(f"Error handling text payment reference: {e}")
        await update.message.reply_text(
            "Ocurrió un error al procesar tu referencia. Por favor, inténtalo de nuevo más tarde."
        )

async def confirmar_pago_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment confirmation from admin."""
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Uso correcto: /confirmar_pago [chat_id_usuario] [tipo_sesion]"
        )
        return

    try:
        chat_id_usuario = int(context.args[0])
        tipo_sesion_elegida = context.args[1]

        if chat_id_usuario not in pagos_pendientes:
            await update.message.reply_text(
                f"No se encontró información de pago pendiente para el usuario {chat_id_usuario}."
            )
            return

        info_pago = pagos_pendientes[chat_id_usuario]
        nombre_usuario = info_pago['nombre_usuario']

        # Activate session
        conversaciones_usuarios[chat_id_usuario] = {
            'tipo_sesion': tipo_sesion_elegida,
            'nombre_usuario': nombre_usuario,
            'conversation_history': [],
            'estado': 'activa',
            'servicio': info_pago.get('servicio', 'coach_motivacional')
        }

        # Remove from pending payments
        del pagos_pendientes[chat_id_usuario]

        # Send confirmation to user
        session_name = format_session_name(tipo_sesion_elegida)
        mensaje_usuario = (
            f"¡Perfecto, {nombre_usuario}! Tu pago ha sido confirmado y activado. ✅\n\n"
            f"Ahora puedes hacer todas las preguntas que necesites. Estoy aquí para ayudarte. 😊"
        
        )

        await context.bot.send_message(
            chat_id=chat_id_usuario,
            text=mensaje_usuario,
            reply_markup=ReplyKeyboardRemove()
        )

        # Start timer for extended session
        if tipo_sesion_elegida == TIPO_SESION_EXTENDIDA:
            asyncio.create_task(iniciar_temporizador_extendida(context, chat_id_usuario))

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Pago confirmado para {nombre_usuario} (ID: {chat_id_usuario}). "
            f"Se activó la {session_name}."
        )
        logger.info(f"Payment confirmed for {chat_id_usuario}, {session_name} activated.")

    except ValueError:
        await update.message.reply_text("El chat_id debe ser un número válido.")
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        await update.message.reply_text("Error al confirmar el pago. Por favor, intenta de nuevo.")

async def responder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin response command to send AI response to user."""
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso correcto: /responder [chat_id_usuario] [respuesta_completa]\n"
            "Ejemplo: /responder 123456789 Tu respuesta de AI aquí..."
        )
        return

    try:
        chat_id_usuario = int(context.args[0])
        respuesta = ' '.join(context.args[1:])

        # Send response to user
        await context.bot.send_message(
            chat_id=chat_id_usuario,
            text=respuesta
        )

        # Check if it's a standard session that should end after response
        if chat_id_usuario in conversaciones_usuarios:
            sesion = conversaciones_usuarios[chat_id_usuario]
            if sesion.get('tipo_sesion') == TIPO_SESION_ESTANDAR and sesion.get('estado') == 'activa':
                # End standard session after response
                await finalizar_sesion_estandar(context, chat_id_usuario)
                logger.info(f"Standard session ended for {chat_id_usuario} after responder command")

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Respuesta enviada al usuario {chat_id_usuario}"
        )
        logger.info(f"Admin response sent to {chat_id_usuario}")

        # Remove from pending questions if exists
        if chat_id_usuario in preguntas_pendientes:
            del preguntas_pendientes[chat_id_usuario]

    except ValueError:
        await update.message.reply_text("El chat_id debe ser un número válido.")
    except Exception as e:
        logger.error(f"Error sending admin response: {e}")
        await update.message.reply_text("Error al enviar la respuesta. Por favor, intenta de nuevo.")

async def responder_rapido_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick response command to last user."""
    if not update.message:
        return
        
    # Check admin permissions
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        logger.warning(f"Unauthorized /r command attempt from {update.message.chat.id}")
        return

    logger.info(f"Admin using /r command. Last user: {utils.ultimo_usuario_pregunta}")
    logger.info(f"Pending questions: {list(preguntas_pendientes.keys())}")

    if not utils.ultimo_usuario_pregunta:
        await update.message.reply_text(
            "No hay usuario reciente al cual responder. Usa /pendientes para ver preguntas pendientes."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /r [tu_respuesta_aquí]\n"
            "Ejemplo: /r Gracias por tu pregunta, aquí está mi respuesta..."
        )
        return

    try:
        respuesta = ' '.join(context.args)
        chat_id_usuario = utils.ultimo_usuario_pregunta

        # Send response to user
        await context.bot.send_message(
            chat_id=chat_id_usuario,
            text=respuesta
        )

        # Get user name for confirmation
        nombre_usuario = "Usuario"
        if chat_id_usuario in preguntas_pendientes:
            nombre_usuario = preguntas_pendientes[chat_id_usuario]['nombre']
            del preguntas_pendientes[chat_id_usuario]

        # Check if it's a standard session that should end after response
        if chat_id_usuario in conversaciones_usuarios:
            sesion = conversaciones_usuarios[chat_id_usuario]
            if sesion.get('tipo_sesion') == TIPO_SESION_ESTANDAR and sesion.get('estado') == 'activa':
                # End standard session after response
                await finalizar_sesion_estandar(context, chat_id_usuario)
                logger.info(f"Standard session ended for {chat_id_usuario} after admin response")

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Respuesta rápida enviada a {nombre_usuario} (ID: {chat_id_usuario})"
        )
        logger.info(f"Quick response sent to {chat_id_usuario}")

    except Exception as e:
        logger.error(f"Error sending quick response: {e}")
        await update.message.reply_text("Error al enviar la respuesta rápida.")

async def pendientes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending questions."""
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    if not preguntas_pendientes:
        await update.message.reply_text("No hay preguntas pendientes.")
        return

    mensaje = "📋 **Preguntas Pendientes:**\n\n"
    for i, (chat_id, info) in enumerate(preguntas_pendientes.items(), 1):
        timestamp = info['timestamp'].strftime("%H:%M")
        consulta_formateada = f'"{info["nombre"]}: {info["pregunta"]}"'
        mensaje += (
            f"**{i}.** {info['nombre']} (ID: `{chat_id}`) - {timestamp}\n"
            f"💬 `{consulta_formateada}`\n"
            f"⚡ Responder: `/r{i} [respuesta]`\n\n"
        )

    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

async def ultima_pregunta_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last question received."""
    if not update.message:
        return
        
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    if not utils.ultimo_usuario_pregunta:
        await update.message.reply_text("No hay ninguna pregunta reciente.")
        return

    if utils.ultimo_usuario_pregunta in preguntas_pendientes:
        info = preguntas_pendientes[utils.ultimo_usuario_pregunta]
        timestamp = info['timestamp'].strftime("%H:%M")
        consulta_formateada = f'"{info["nombre"]}: {info["pregunta"]}"'
        mensaje = (
            f"🔄 **Última Pregunta Recibida:**\n\n"
            f"👤 **{info['nombre']}** (ID: `{utils.ultimo_usuario_pregunta}`) - {timestamp}\n\n"
            f"💬 **Consulta para ChatGPT:**\n"
            f"`{consulta_formateada}`\n\n"
            f"⚡ **Responder:** `/r [tu_respuesta]`"
        )
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"Última pregunta fue del usuario ID: {utils.ultimo_usuario_pregunta}")

async def responder_numerado_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle numbered response commands /r1, /r2, etc."""
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    # Extract number from command
    command = update.message.text.split()[0]  # e.g., "/r1"
    numero = int(command[2:])  # Extract number from "/r1" -> "1"

    if not preguntas_pendientes:
        await update.message.reply_text("No hay preguntas pendientes.")
        return

    if not context.args:
        await update.message.reply_text(f"Uso: {command} [tu_respuesta_aquí]")
        return

    # Get the nth question
    preguntas_lista = list(preguntas_pendientes.items())
    if numero > len(preguntas_lista):
        await update.message.reply_text(f"No existe la pregunta número {numero}.")
        return

    chat_id_usuario, info = preguntas_lista[numero - 1]
    respuesta = ' '.join(context.args)

    try:
        # Send response to user
        await context.bot.send_message(
            chat_id=chat_id_usuario,
            text=respuesta
        )

        # Check if it's a standard session that should end after response
        if chat_id_usuario in conversaciones_usuarios:
            sesion = conversaciones_usuarios[chat_id_usuario]
            if sesion.get('tipo_sesion') == TIPO_SESION_ESTANDAR and sesion.get('estado') == 'activa':
                # End standard session after response
                await finalizar_sesion_estandar(context, chat_id_usuario)
                logger.info(f"Standard session ended for {chat_id_usuario} after numbered response")

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Respuesta #{numero} enviada a {info['nombre']} (ID: {chat_id_usuario})"
        )
        logger.info(f"Numbered response #{numero} sent to {chat_id_usuario}")

        # Remove from pending questions
        del preguntas_pendientes[chat_id_usuario]

    except Exception as e:
        logger.error(f"Error sending numbered response: {e}")
        await update.message.reply_text(f"Error al enviar la respuesta #{numero}.")

async def respuesta_rapida_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick response template command."""
    if not update.message:
        return
        
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    await update.message.reply_text(
        "📝 **Comandos de Respuesta Rápida:**\n\n"
        "⚡ `/r [respuesta]` - Responder al último usuario\n"
        "📋 `/pendientes` - Ver todas las preguntas pendientes\n"
        "🔄 `/ultima` - Ver la última pregunta recibida\n"
        "🔢 `/r1`, `/r2`, etc. - Responder pregunta específica por número\n\n"
        "💡 **Ejemplo:**\n"
        "`/r Gracias por tu pregunta, aquí está mi respuesta...`",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin status and system information."""
    if not update.message:
        return
        
    if update.message.chat.id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("No tienes permisos para usar este comando.")
        return

    # System status
    num_pendientes = len(preguntas_pendientes)
    num_sesiones_activas = len([s for s in conversaciones_usuarios.values() if s.get('estado') == 'activa'])
    num_pagos_pendientes = len(pagos_pendientes)
    
    mensaje = (
        f"🤖 **Estado del Sistema Apoyo Integral**\n\n"
        f"📊 **Estadísticas Actuales:**\n"
        f"• Preguntas pendientes: {num_pendientes}\n"
        f"• Sesiones activas: {num_sesiones_activas}\n"
        f"• Pagos pendientes: {num_pagos_pendientes}\n\n"
        f"👤 **Último usuario con pregunta:** {utils.ultimo_usuario_pregunta or 'Ninguno'}\n\n"
        f"🔧 **Comandos Disponibles:**\n"
        f"• `/r [respuesta]` - Responder al último\n"
        f"• `/pendientes` - Ver todas las preguntas\n"
        f"• `/ultima` - Ver última pregunta\n"
        f"• `/confirmar_pago [user_id] [tipo_sesion]`\n"
        f"• `/rapida` - Ver ayuda de comandos\n\n"
        f"✅ **Sistema funcionando correctamente**"
    )
    
    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages from users."""
    if not update.effective_user or not update.message:
        return

    chat_id_usuario = update.message.chat.id
    texto_usuario = update.message.text
    nombre_usuario = update.effective_user.first_name or "Usuario"

    # Skip admin messages
    if chat_id_usuario == YOUR_TELEGRAM_ID:
        return

    # Check if this is a returning user and handle appropriately
    from utils import handle_returning_user
    if await handle_returning_user(update, context):
        return

    # Check if it's a payment reference (numbers, letters, or specific patterns)
    payment_reference_pattern = r'^[A-Za-z0-9\-_]{4,20}$'
    if re.match(payment_reference_pattern, texto_usuario.strip()) and chat_id_usuario in pagos_pendientes:
        await handle_text_payment_reference(update, context, texto_usuario.strip())
        return

    # Handle service selection
    if texto_usuario in MENU_SERVICIOS_A_TIPO:
        servicio_elegido = MENU_SERVICIOS_A_TIPO[texto_usuario]
        
        # Show service description
        resumen = RESUMEN_SERVICIOS.get(servicio_elegido, "Servicio de apoyo integral disponible.")
        keyboard = generate_session_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Store selected service in pending payment info if exists
        if chat_id_usuario in pagos_pendientes:
            pagos_pendientes[chat_id_usuario]['servicio'] = servicio_elegido
        
        await update.message.reply_text(
            f"{resumen}\n\n"
            f"¿Qué tipo de sesión te gustaría solicitar?",
            reply_markup=reply_markup
        )
        logger.info(f"User {nombre_usuario} selected service: {servicio_elegido}")
        return

    # Handle session type selection
    if texto_usuario in MENU_OPCIONES_A_TIPO:
        tipo_sesion_elegida = MENU_OPCIONES_A_TIPO[texto_usuario]
        precio_dolares = PRECIO_SESION[tipo_sesion_elegida]
        
        # Store service info before showing payment
        if chat_id_usuario not in pagos_pendientes:
            pagos_pendientes[chat_id_usuario] = {
                'nombre_usuario': nombre_usuario,
                'servicio': 'coach_motivacional'  # Default service
            }
        
        pagos_pendientes[chat_id_usuario].update({
            'tipo_sesion_elegida': tipo_sesion_elegida,
            'precio_dolares': precio_dolares
        })
        
        await mostrar_informacion_pago(update, context, tipo_sesion_elegida, precio_dolares)
        return

    # Handle "Volver al Menú Principal"
    if texto_usuario == "🏠 Volver al Menú Principal":
        keyboard = generate_service_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"¡Perfecto, {nombre_usuario}! ¿En qué puedo ayudarte hoy? Elige una opción:",
            reply_markup=reply_markup
        )
        return

    # Handle active session questions
    if chat_id_usuario in conversaciones_usuarios:
        sesion = conversaciones_usuarios[chat_id_usuario]
        if sesion.get('estado') == 'activa':
            # Add to conversation history
            sesion['conversation_history'].append({
                'timestamp': datetime.datetime.now(),
                'user_message': texto_usuario
            })
            
            # Notify admin
            await notify_admin_user_question(context, chat_id_usuario, nombre_usuario, texto_usuario)
            
            # Send confirmation to user
            await update.message.reply_text(
                "He recibido tu pregunta. Te responderé pronto. 😊"
            )
            logger.info(f"Question received from active session user {chat_id_usuario}")
            return

    # Default response for unrecognized messages
    keyboard = generate_service_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"¡Hola {nombre_usuario}! Para poder ayudarte, por favor selecciona una de las opciones del menú:",
        reply_markup=reply_markup
    )
