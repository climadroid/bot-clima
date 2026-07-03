import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext
import requests
import logging
from datetime import datetime, timezone, timedelta

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración del bot de Telegram (variables de entorno en Railway)
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
API_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
API_KEY = os.getenv("WEATHER_API_KEY")

# Emojis según el clima
WEATHER_EMOJIS = {
    'clear sky': '☀️', 'few clouds': '🌤️', 'scattered clouds': '⛅',
    'broken clouds': '☁️', 'overcast clouds': '☁️', 'shower rain': '🌧️',
    'rain': '🌧️', 'light rain': '🌦️', 'moderate rain': '🌧️',
    'heavy intensity rain': '⛈️', 'thunderstorm': '⛈️', 'snow': '❄️',
    'light snow': '🌨️', 'mist': '🌫️', 'haze': '🌫️', 'fog': '🌫️',
}

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("☁️ Clima Actual", callback_data='clima'),
         InlineKeyboardButton("🌅 Pronóstico 5 días", callback_data='pronostico')],
        [InlineKeyboardButton("🕐 Hora", callback_data='hora'),
         InlineKeyboardButton("👨‍💻 Creador", callback_data='creador')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌤️ *Bot del Clima*\n\n"
        "¡Bienvenido! Selecciona una opción:\n\n"
        "_Creado por @daxurymer_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def menu_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'clima':
        await query.edit_message_text("Usa el comando /clima <ciudad>\n\nEjemplo: /clima Madrid")

    elif query.data == 'pronostico':
        await query.edit_message_text("Usa el comando /pronostico <ciudad>\n\nEjemplo: /pronostico Madrid")

    elif query.data == 'hora':
        await query.edit_message_text("Por favor, usa el comando /hora <ciudad> para obtener la hora local.\n\nEjemplo: /hora Tokyo")

    elif query.data == 'creador':
        await query.edit_message_text(
            "👨‍💻 *Creador del Bot*\n\n"
            "Este bot fue creado por *daxurymer* 🚀\n\n"
            "📌 GitHub: github.com/climadroid\n"
            "🤖 Gracias por usar el bot!",
            parse_mode='Markdown'
        )

async def get_weather(update: Update, context: CallbackContext) -> None:
    try:
        city = " ".join(context.args) if context.args else ""
        if not city:
            await update.message.reply_text("Por favor, proporciona una ciudad después del comando.\n\nEjemplo: /clima Madrid")
            return

        response = requests.get(API_WEATHER, params={
            'q': city,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'es'
        }, timeout=10).json()

        logger.info(f"Respuesta API para '{city}': cod={response.get('cod')}")

        if int(response.get('cod', 0)) != 200:
            await update.message.reply_text("No se pudo encontrar el clima para esa ciudad. Intenta con el nombre en inglés o verifica la ortografía.")
            return

        weather_info = response['weather'][0]['description'].capitalize()
        temp = response['main']['temp']
        feels_like = response['main']['feels_like']
        humidity = response['main']['humidity']

        mensaje = (
            f"🌍 *Clima en {city}*\n\n"
            f"☁️ {weather_info}\n"
            f"🌡️ Temperatura: {temp}°C\n"
            f"🤒 Sensación térmica: {feels_like}°C\n"
            f"💧 Humedad: {humidity}%"
        )
        await update.message.reply_text(mensaje, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text("⏳ La consulta tardó demasiado. Intenta de nuevo.")
    except requests.exceptions.ConnectionError:
        await update.message.reply_text("🔌 Error de conexión. Verifica tu internet.")
    except Exception as e:
        logger.error(f"Error al obtener el clima: {e}")
        await update.message.reply_text(f"❌ Error al obtener el clima: {str(e)}")

def get_weather_emoji(description):
    """Devuelve un emoji según la descripción del clima en inglés."""
    desc_lower = description.lower()
    for key, emoji in WEATHER_EMOJIS.items():
        if key in desc_lower:
            return emoji
    return '🌡️'

async def pronostico(update: Update, context: CallbackContext) -> None:
    try:
        city = " ".join(context.args) if context.args else ""
        if not city:
            await update.message.reply_text("Por favor, proporciona una ciudad.\n\nEjemplo: /pronostico Madrid")
            return

        response = requests.get(API_FORECAST, params={
            'q': city,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'es',
            'cnt': 40  # 5 días x 8 (cada 3 horas)
        }, timeout=10).json()

        if int(response.get('cod', 0)) != 200:
            await update.message.reply_text("No se pudo encontrar esa ciudad. Verifica el nombre.")
            return

        # Agrupar por día y obtener resumen diario
        dias = {}
        for item in response['list']:
            fecha = item['dt_txt'].split(' ')[0]
            if fecha not in dias:
                dias[fecha] = {
                    'temp_min': item['main']['temp_min'],
                    'temp_max': item['main']['temp_max'],
                    'desc': item['weather'][0]['description'],
                    'desc_en': item['weather'][0].get('main', ''),
                }
            else:
                dias[fecha]['temp_min'] = min(dias[fecha]['temp_min'], item['main']['temp_min'])
                dias[fecha]['temp_max'] = max(dias[fecha]['temp_max'], item['main']['temp_max'])

        mensaje = f"🌅 *Pronóstico para {city}*\n"
        for i, (fecha, data) in enumerate(dias.items()):
            if i >= 5:  # Máximo 5 días
                break
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            dia_nombre = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][dt.weekday()]
            emoji = get_weather_emoji(data['desc_en'])
            mensaje += (
                f"\n{emoji} *{dia_nombre} {dt.strftime('%d/%m')}*\n"
                f"     ↓ {data['temp_min']:.0f}°C  ↑ {data['temp_max']:.0f}°C\n"
                f"     {data['desc'].capitalize()}\n"
            )

        await update.message.reply_text(mensaje, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text("⏳ La consulta tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error en pronóstico: {e}")
        await update.message.reply_text(f"❌ Error al obtener el pronóstico: {str(e)}")

async def hora(update: Update, context: CallbackContext) -> None:
    try:
        city = " ".join(context.args) if context.args else ""
        if not city:
            await update.message.reply_text("Por favor, proporciona una ciudad.\n\nEjemplo: /hora Tokyo")
            return

        response = requests.get(API_WEATHER, params={
            'q': city,
            'appid': API_KEY,
        }, timeout=10).json()

        if int(response.get('cod', 0)) != 200:
            await update.message.reply_text("No se pudo encontrar esa ciudad. Verifica el nombre.")
            return

        # Obtener la zona horaria de la ciudad (offset en segundos)
        tz_offset = response.get('timezone', 0)
        tz = timezone(timedelta(seconds=tz_offset))
        hora_local = datetime.now(tz)

        await update.message.reply_text(
            f"🕐 *Hora en {city}*\n\n"
            f"📅 Fecha: {hora_local.strftime('%d/%m/%Y')}\n"
            f"⏰ Hora: {hora_local.strftime('%H:%M:%S')}\n"
            f"🌐 UTC{'+' if tz_offset >= 0 else ''}{tz_offset // 3600}:{abs(tz_offset % 3600) // 60:02d}",
            parse_mode='Markdown'
        )

    except requests.exceptions.Timeout:
        await update.message.reply_text("⏳ La consulta tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error al obtener la hora: {e}")
        await update.message.reply_text(f"❌ Error al obtener la hora: {str(e)}")

async def creador(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "👨‍💻 *Creador del Bot*\n\n"
        "Este bot fue creado por *daxurymer* 🚀\n\n"
        "📌 GitHub: github.com/climadroid\n"
        "🤖 Gracias por usar el bot!",
        parse_mode='Markdown'
    )

if __name__ == "__main__":
    if not TOKEN or not API_KEY:
        logger.error("❌ Faltan variables de entorno: TELEGRAM_TOKEN y/o WEATHER_API_KEY")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(CommandHandler("clima", get_weather))
    app.add_handler(CommandHandler("pronostico", pronostico))
    app.add_handler(CommandHandler("hora", hora))
    app.add_handler(CommandHandler("creador", creador))

    logger.info("Bot iniciado correctamente.")
    app.run_polling()
