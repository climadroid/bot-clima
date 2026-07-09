import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
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

DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
DIAS_CORTO = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

def get_weather_emoji(description):
    """Devuelve un emoji según la descripción del clima."""
    desc_lower = description.lower()
    for key, emoji in WEATHER_EMOJIS.items():
        if key in desc_lower:
            return emoji
    return '🌡️'

# ─────────────────────────────────────────────
# /start — Menú principal con botón de ubicación
# ─────────────────────────────────────────────
async def start(update: Update, context: CallbackContext) -> None:
    # Botón especial que pide la ubicación del dispositivo
    location_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Enviar mi ubicación", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await update.message.reply_text(
        "📍 *Envía tu ubicación* con el botón de abajo para ver todo de un solo golpe!\n\n"
        "O usa los comandos manuales:",
        reply_markup=location_keyboard,
        parse_mode='Markdown'
    )

    # Menú inline con las opciones manuales
    keyboard = [
        [InlineKeyboardButton("☁️ Clima", callback_data='clima'),
         InlineKeyboardButton("🌅 Pronóstico", callback_data='pronostico')],
        [InlineKeyboardButton("🕐 Hora", callback_data='hora'),
         InlineKeyboardButton("👨‍💻 Creador", callback_data='creador')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌤️ *Bot del Clima*\n\n"
        "También puedes usar los comandos:\n"
        "• /clima <ciudad>\n"
        "• /pronostico <ciudad>\n"
        "• /hora <ciudad>\n\n"
        "_Creado por @daxurymer_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ─────────────────────────────────────────────
# 📍 Ubicación — Todo en un solo mensaje
# ─────────────────────────────────────────────
async def handle_location(update: Update, context: CallbackContext) -> None:
    try:
        lat = update.message.location.latitude
        lon = update.message.location.longitude

        await update.message.reply_text("📡 Obteniendo información de tu ubicación...")

        # 1. Clima actual por coordenadas
        weather_resp = requests.get(API_WEATHER, params={
            'lat': lat, 'lon': lon,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'es'
        }, timeout=10).json()

        if int(weather_resp.get('cod', 0)) != 200:
            await update.message.reply_text("❌ No se pudo obtener el clima para tu ubicación.")
            return

        city = weather_resp.get('name', 'Tu ubicación')
        country = weather_resp.get('sys', {}).get('country', '')
        weather_desc = weather_resp['weather'][0]['description'].capitalize()
        weather_main = weather_resp['weather'][0].get('main', '')
        temp = weather_resp['main']['temp']
        feels_like = weather_resp['main']['feels_like']
        humidity = weather_resp['main']['humidity']
        wind = weather_resp.get('wind', {}).get('speed', 0)
        emoji_clima = get_weather_emoji(weather_main)

        # 2. Hora local
        tz_offset = weather_resp.get('timezone', 0)
        tz = timezone(timedelta(seconds=tz_offset))
        hora_local = datetime.now(tz)
        dia_semana = DIAS_SEMANA[hora_local.weekday()]

        # 3. Amanecer y atardecer
        sunrise_ts = weather_resp.get('sys', {}).get('sunrise', 0)
        sunset_ts = weather_resp.get('sys', {}).get('sunset', 0)
        sunrise = datetime.fromtimestamp(sunrise_ts, tz=tz).strftime('%H:%M')
        sunset = datetime.fromtimestamp(sunset_ts, tz=tz).strftime('%H:%M')

        # 4. Pronóstico 3 días
        forecast_resp = requests.get(API_FORECAST, params={
            'lat': lat, 'lon': lon,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'es',
            'cnt': 24  # 3 días
        }, timeout=10).json()

        forecast_text = ""
        if int(forecast_resp.get('cod', 0)) == 200:
            dias = {}
            for item in forecast_resp['list']:
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

            forecast_text = "\n━━━━━━━━━━━━━━━━━━━━\n🗓️ *Próximos días:*\n"
            for i, (fecha, data) in enumerate(dias.items()):
                if i == 0:  # Saltar hoy
                    continue
                if i >= 4:
                    break
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                dia_nombre = DIAS_CORTO[dt.weekday()]
                f_emoji = get_weather_emoji(data['desc_en'])
                forecast_text += (
                    f"\n{f_emoji} *{dia_nombre} {dt.strftime('%d/%m')}*"
                    f"  ↓{data['temp_min']:.0f}° ↑{data['temp_max']:.0f}°"
                    f"  {data['desc'].capitalize()}"
                )

        # Construir mensaje completo
        mensaje = (
            f"📍 *{city}, {country}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"🕐 *{dia_semana} {hora_local.strftime('%d/%m/%Y')}*\n"
            f"⏰ Hora local: *{hora_local.strftime('%H:%M:%S')}*\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji_clima} *{weather_desc}*\n"
            f"\n"
            f"🌡️ Temperatura: *{temp:.1f}°C*\n"
            f"🤒 Sensación: {feels_like:.1f}°C\n"
            f"💧 Humedad: {humidity}%\n"
            f"💨 Viento: {wind} m/s\n"
            f"\n"
            f"🌅 Amanecer: {sunrise}\n"
            f"🌇 Atardecer: {sunset}"
            f"{forecast_text}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_Creado por @daxurymer_ 🚀"
        )

        await update.message.reply_text(mensaje, parse_mode='Markdown')

    except requests.exceptions.Timeout:
        await update.message.reply_text("⏳ La consulta tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error al procesar ubicación: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ─────────────────────────────────────────────
# Callbacks del menú inline
# ─────────────────────────────────────────────
async def menu_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'clima':
        await query.edit_message_text("Usa el comando /clima <ciudad>\n\nEjemplo: /clima Madrid")

    elif query.data == 'pronostico':
        await query.edit_message_text("Usa el comando /pronostico <ciudad>\n\nEjemplo: /pronostico Madrid")

    elif query.data == 'hora':
        await query.edit_message_text("Usa el comando /hora <ciudad>\n\nEjemplo: /hora Tokyo")

    elif query.data == 'creador':
        await query.edit_message_text(
            "👨‍💻 *Creador del Bot*\n\n"
            "Este bot fue creado por *daxurymer* 🚀\n\n"
            "📌 GitHub: github.com/climadroid\n"
            "🤖 Gracias por usar el bot!",
            parse_mode='Markdown'
        )

# ─────────────────────────────────────────────
# /clima — Clima por ciudad
# ─────────────────────────────────────────────
async def get_weather(update: Update, context: CallbackContext) -> None:
    try:
        city = " ".join(context.args) if context.args else ""
        if not city:
            await update.message.reply_text("Por favor, proporciona una ciudad.\n\nEjemplo: /clima Madrid")
            return

        response = requests.get(API_WEATHER, params={
            'q': city,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'es'
        }, timeout=10).json()

        logger.info(f"Respuesta API para '{city}': cod={response.get('cod')}")

        if int(response.get('cod', 0)) != 200:
            await update.message.reply_text("No se pudo encontrar el clima para esa ciudad.")
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

# ─────────────────────────────────────────────
# /pronostico — Pronóstico 5 días
# ─────────────────────────────────────────────
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
            'cnt': 40
        }, timeout=10).json()

        if int(response.get('cod', 0)) != 200:
            await update.message.reply_text("No se pudo encontrar esa ciudad. Verifica el nombre.")
            return

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
            if i >= 5:
                break
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            dia_nombre = DIAS_CORTO[dt.weekday()]
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

# ─────────────────────────────────────────────
# /hora — Hora por ciudad
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# /creador
# ─────────────────────────────────────────────
async def creador(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "👨‍💻 *Creador del Bot*\n\n"
        "Este bot fue creado por *daxurymer* 🚀\n\n"
        "📌 GitHub: github.com/climadroid\n"
        "🤖 Gracias por usar el bot!",
        parse_mode='Markdown'
    )

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN or not API_KEY:
        logger.error("❌ Faltan variables de entorno: TELEGRAM_TOKEN y/o WEATHER_API_KEY")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CommandHandler("clima", get_weather))
    app.add_handler(CommandHandler("pronostico", pronostico))
    app.add_handler(CommandHandler("hora", hora))
    app.add_handler(CommandHandler("creador", creador))

    logger.info("Bot iniciado correctamente.")
    app.run_polling()
