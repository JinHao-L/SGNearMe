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

# Telegram chat id with developer for sending error reports
DEVELOPER_CHAT_ID = 521610007;

# Pos of user in (lat, lng) format
current_pos = None

############################# Keyboards #########################################
def location_prompt_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text="📍Share Location", request_location=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def categories_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Education", "Recreation"],
                ["Community", "Health"],
                ["Cultural", "Emergency Services"],
                [KeyboardButton(text="📍Update My Location", request_location=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def education_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Preschools", "Kindergartens"],
                    ["Private Education", "Libraries"],
                    ["CET Centres"],
                    ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def recreation_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Tourist Spot", "Hotels"],
                ["Parks"],
                ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def community_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Hawker Centres", "Childcare"],
                ["Supermarkets", "Money Changer"],
                ["Gyms", "RC", "CC"],
                ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def health_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Pharmacy", "CHAS Clinics"],
                ["Hospitals"],
                ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def emergency_services_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Police Station", "Fire Station"],
                ["AEDs"],
                ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cultural_submenu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [["Museums", "Monuments"],
                ["Historic Sites"],
                ["All Categories"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


############################# Bot #########################################
def start(update: Update, context: CallbackContext) -> None:
    """Start bot and prompt for location"""
    username = update.message.from_user.username
    text = "Hello " + username + "!\nLet's find out whats near you.\n\nTo begin share with me your location and select a search query from the categories below\n"

    update.message.reply_text(text, reply_markup=location_prompt_keyboard())

def help(update: Update, context: CallbackContext) -> None:
    """Get decription of bot and functionalities"""
    text = "Hello there! This is a location bot powered by OneMap API.\n\nThis bot provides many useful information, such as the supermarkets, community centres or AEDs near you. These information are contributed and updated by government agencies.\n\nTo begin you can use /menu to access the main menu. Remember to share your latest location with me before starting a search query!\nYou can use /map to get a (night version) map of your current location"

    update.message.reply_text(text)

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

def main_menu(update: Update, context: CallbackContext) -> None:
    """Get the main menu with the categories."""
    text = "Select a category or update your location"
    update.message.reply_text(text, reply_markup=categories_menu_keyboard())

def location_prompt(update: Update, context: CallbackContext) -> None:
    """Prompt the user for a location."""
    text = "I do not have your location. Share with me your location"
    update.message.reply_text(text, reply_markup=location_prompt_keyboard())

def share_location(update: Update, context: CallbackContext) -> None:
    """Update user location"""
    global current_pos
    if (update.edited_message) :
        current_pos = (update.edited_message.location.latitude, update.edited_message.location.longitude)
    elif (update.message) :
        current_pos = (update.message.location.latitude, update.message.location.longitude)

    logger.info("Location updated to " + ','.join(map(str, current_pos)))
    update.message.reply_text('Select a category', reply_markup=categories_menu_keyboard())

def get_nearby_places(update: Update, context: CallbackContext) -> None:
    """Query for indicated facilities near the user"""
    if (current_pos == None) :
        # prompt for location
        return location_prompt(update, context)

    result = onemap.get_nearby_places(update.message.text, current_pos[0], current_pos[1])
    update.message.reply_text(result, parse_mode=ParseMode.HTML)

def get_my_map(update: Update, context: CallbackContext) -> None :
    """Get map of user"""
    if (current_pos == None) :
        # prompt for location
        return location_prompt(update, context)

    url = onemap.getMapUrl(current_pos[0], current_pos[1])
    logger.info("Showing img: " + url)
    update.message.bot.send_photo(chat_id = update.message.chat.id, photo=url)

def get_category(update: Update, context: CallbackContext) -> None:
    """Get 2nd level keyboard choices"""
    message = update.message.text;
    if (message == "Education") :
        reply_choice = education_submenu_keyboard()
    elif (message == "Recreation") :
        reply_choice = recreation_submenu_keyboard()
    elif (message == "Community") :
        reply_choice = community_submenu_keyboard()
    elif (message == "Health") :
        reply_choice = health_submenu_keyboard()
    elif (message == "Emergency Services") :
        reply_choice = emergency_services_submenu_keyboard()
    elif (message == "Cultural") :
        reply_choice = cultural_submenu_keyboard()
    else :
        raise Exception("No such category found")

    update.message.reply_text("Select a search query", reply_markup=reply_choice)

############################# Main #########################################
def main():
    """Start the bot"""
    # Create the Updater with bot's token
    updater = Updater(config.BOT_TOKEN, use_context=True)
    PORT = int(os.environ.get('PORT', '8443'))
    NAME = "rocky-reaches-93032"

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", main_menu))
    dispatcher.add_handler(CommandHandler("map", get_my_map))
    dispatcher.add_handler(CommandHandler("help", help))

    # Message handler
    dispatcher.add_handler(MessageHandler(Filters.regex('^(Education|Recreation|Community|Health|Emergency Services|Cultural)$'),get_category))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(All Categories)$'),main_menu))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, get_nearby_places))
    dispatcher.add_handler(MessageHandler(Filters.location, share_location))

    # Error handler
    dispatcher.add_error_handler(error_handler)

    # Start bot
    updater.start_polling();
    # updater.start_webhook(listen = "0.0.0.0", port = PORT, url_path = config.BOT_TOKEN)
    # updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, config.BOT_TOKEN))

    # Run the bot until bot stopped
    updater.idle()

if __name__ == '__main__':
    main()
