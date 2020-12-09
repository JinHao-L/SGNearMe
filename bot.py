import logging
import traceback
import html
import json
import os

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import onemap
import config

# Enable logging
logging.basicConfig(
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO
)

logger = logging.getLogger(__name__)

DEVELOPER_CHAT_ID = 521610007;

current_pos = (1.304833, 103.831833)

categories = ReplyKeyboardMarkup([
    ["Education", "Recreation"],
    ["Community", "Health"],
    ["Cultural", "Emergency"],
    [KeyboardButton(text="📍Update Location", request_location=True)]
])

cat_education = ReplyKeyboardMarkup([
    ["Preschools", "Kindergartens"],
    ["Private Education", "Libraries"],
    ["CET Centres"],
    ["All Categories"]
], one_time_keyboard=True)

cat_recreation = ReplyKeyboardMarkup([
    ["Tourist Spot", "Hotels"],
    ["Parks"], ["All Categories"]
], one_time_keyboard=True)

cat_community = ReplyKeyboardMarkup([
    ["Hawker Centres", "Childcare"],
    ["Supermarkets", "Money Changer"],
    ["Gyms", "RC", "CC"],
    ["All Categories"]
], one_time_keyboard=True)

cat_health = ReplyKeyboardMarkup([
    ["Pharmacy", "CHAS Clinics"],
    ["Hospitals"], ["All Categories"]
], one_time_keyboard=True)

cat_emergency = ReplyKeyboardMarkup([
    ["Police Station", "Fire Station"],
    ["AEDs"],
    ["All Categories"]
], one_time_keyboard=True)

cat_cultural = ReplyKeyboardMarkup([
    ["Museums", "Monuments"],
    ["Historic Sites"],
    ["All Categories"]
], one_time_keyboard=True)

def start(update: Update, context: CallbackContext) -> None:
    # On start
    username = update.message.from_user.username
    text = "Hello " + username + "!\nLet's find out whats near you.\n\nTo begin share with me your location and select a search query from the categories below\n"
    update.message.reply_text(text, reply_markup=categories)

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello there! This is a location bot powered by OneMap API.\n\nThis bot provides many useful information on nearby places that are contributed and updated by government agencies.\n\nYou can use /menu or /start to access the main menu. Do share your location before starting a search query!")

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log error and send a telegram message to developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
    update.message.reply_text("An unexpected error has occured! The developer will be informed")

def mainMenu(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Select a category or update your location', reply_markup=categories)

def getMyMap(update: Update, context: CallbackContext) -> None :
    url = onemap.getMapUrl(current_pos[0], current_pos[1])
    logger.info("Showing img: " + url)
    update.message.bot.send_photo(chat_id = update.message.chat.id, photo=url)

def updateLocation(update: Update, context: CallbackContext) -> None:
    """Update location"""
    global current_pos
    current_pos = (update.message.location.latitude, update.message.location.longitude)
    logger.info("Location updated to " + ','.join(map(str, current_pos)))

def getNearbyPlaces(update: Update, context: CallbackContext) -> None:
    """Get nearby"""
    result = onemap.getNearbyPlaces(update.message.text, current_pos[0], current_pos[1])
    update.message.reply_text(result, parse_mode=ParseMode.HTML)



def getCategory(update: Update, context: CallbackContext) -> None:
    message = update.message.text;
    if (message == "Education") :
        reply_choice = cat_education
    elif (message == "Recreation") :
        reply_choice = cat_recreation
    elif (message == "Community") :
        reply_choice = cat_community
    elif (message == "Health") :
        reply_choice = cat_health
    elif (message == "Emergency") :
        reply_choice = cat_emergency
    elif (message == "Cultural") :
        reply_choice = cat_cultural
    else :
        raise Exception("No such category found")

    update.message.reply_text("Select a search query", reply_markup=reply_choice)



def main():
    """Start the bot"""
    # Create the Updater with bot's token
    updater = Updater(config.BOT_TOKEN, use_context=True)
    PORT = int(os.environ.get('PORT', '8443'))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", mainMenu))
    dispatcher.add_handler(CommandHandler("map", getMyMap))
    dispatcher.add_handler(CommandHandler("help", help))
    # dispatcher.add_handler(CommandHandler("where", getCurrLocation))

    dispatcher.add_handler(MessageHandler(Filters.regex('^(Education|Recreation|Community|Health|Emergency|Cultural)$'),getCategory))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(All Categories)$'),mainMenu))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, getNearbyPlaces))
    dispatcher.add_handler(MessageHandler(Filters.location, updateLocation))

    # error handler
    dispatcher.add_error_handler(error_handler)

    # startBot
    updater.start_webhook(listen = "0.0.0.0", port = PORT, url_path = config.BOT_TOKEN)
    updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, TOKE))

    # Run the bot until bot stopped
    updater.idle()

if __name__ == '__main__':
    main()
