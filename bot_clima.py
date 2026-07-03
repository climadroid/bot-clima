import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext
import requests
import logging

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración del bot de Telegram (variables de entorno en Railway)
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
API_KEY = os.getenv("WEATHER_API_KEY")

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("☁️ Consultar Clima", callback_data='clima')],
        [InlineKeyboardButton("👨‍💻 Creador", callback_data='creador')]
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
        await query.edit_message_text("Por favor, usa el comando /clima <ciudad> para obtener el clima.\n\nEjemplo: /clima Madrid")

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
    app.add_handler(CommandHandler("creador", creador))

    logger.info("Bot iniciado correctamente.")
    app.run_polling()
