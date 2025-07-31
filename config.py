import os
import logging

logger = logging.getLogger(__name__)

# Telegram Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
YOUR_TELEGRAM_ID = os.environ.get('YOUR_TELEGRAM_ID')

if YOUR_TELEGRAM_ID:
    try:
        YOUR_TELEGRAM_ID = int(YOUR_TELEGRAM_ID)
    except ValueError:
        logger.error(f"YOUR_TELEGRAM_ID '{YOUR_TELEGRAM_ID}' is not a valid number.")
        YOUR_TELEGRAM_ID = None

# Payment Information
NUMERO_TELEFONO = os.environ.get('NUMERO_TELEFONO')
CEDULA_IDENTIDAD = os.environ.get('CEDULA_IDENTIDAD')
BANCO = os.environ.get('BANCO')

# Exchange Rate Configuration
TASA_BCV_STR = os.environ.get('TASA_BCV')
if TASA_BCV_STR:
    TASA_BCV_STR_CLEAN = TASA_BCV_STR.replace(',', '.')
    try:
        TASA_BCV = float(TASA_BCV_STR_CLEAN)
    except ValueError:
        logger.error(f"Could not convert TASA_BCV '{TASA_BCV_STR}' to number. Using default value 36.50")
        TASA_BCV = 36.50
else:
    TASA_BCV = 36.50

# Session Types and Prices
TIPO_SESION_ESTANDAR = "sesion_estandar"
TIPO_SESION_EXTENDIDA = "sesion_extendida"

MENU_OPCIONES_A_TIPO = {
    '⭐ Sesión Estándar (2$)': TIPO_SESION_ESTANDAR,
    '💎 Sesión Extendida (4$)': TIPO_SESION_EXTENDIDA
}

PRECIO_SESION = {
    TIPO_SESION_ESTANDAR: 2.0,
    TIPO_SESION_EXTENDIDA: 4.0
}

# Session Configuration
TIEMPO_SESION_EXTENDIDA_MINUTOS = 20

# Service Types
SERVICIO_COACH = "coach_motivacional"
SERVICIO_APOYO = "apoyo_emocional"
SERVICIO_DOCENTES = "ayuda_docentes"

MENU_SERVICIOS_A_TIPO = {
    '🚀 Coach Motivacional': SERVICIO_COACH,
    '💙 Apoyo Emocional': SERVICIO_APOYO,
    '📚 Ayuda para Docentes': SERVICIO_DOCENTES
}
