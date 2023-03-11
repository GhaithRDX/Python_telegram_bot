import telegram
import pytube
import os

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

from decouple import config


BOT_TOKEN = config('BOT_TOKEN')

# Define the states
TYPE, QUALITY , DOWNLOAD = range(3)

# Your Telegram Bot token
TOKEN = BOT_TOKEN

# Set up the bot
bot = telegram.Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Handler function for /start command
def start(update, context):
    message = "Welcome to YouTube Downloader Bot! Send me a YouTube video link to get started."
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return TYPE

# Handler function for download type
def type_handler(update, context):
    # Get the message text
    message_text = update.message.text
    
    # Try to create a PyTube object from the URL
    try:
        yt = pytube.YouTube(message_text)
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid YouTube video URL.")
        return ConversationHandler.END
    
    # Set the context for the next message handler
    context.user_data['yt'] = yt
    context.user_data['url'] = message_text
    
    # Ask the user for the download type
    keyboard = [['Video', 'Audio']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    message = "What do you want to download?"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    
    return QUALITY
# Handler function for download quality
def quality_handler(update, context):
    # Get the message text
    message_text = update.message.text
    
    # Get the PyTube object and selected download type
    yt = context.user_data['yt']
    download_type = message_text.lower()
    # Filter the streams based on the download type
    if download_type == 'video':
        streams = yt.streams.filter(only_video=True).order_by('resolution').desc()
    else:
        streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
    # Set the context for the next message handler
    context.user_data['streams'] = streams
    
    # Create a list of quality options
    keyboard = [[str(s.itag) + ' - ' + (s.resolution if download_type == 'video' else s.abr)] for s in streams]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    message = "Choose the download quality:"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return DOWNLOAD  # Change the state to DOWNLOAD

# Handler function for download
def download_handler(update, context):
    # Get the message text
    message_text = update.message.text
    
    # Get the selected stream
    streams = context.user_data['streams']
    stream = streams.get_by_itag(int(message_text.split(' ')[0]))
    
    # Download the video
    file_path = stream.download()
    
    # Send the downloaded file to the user
    context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, 'rb'), timeout=100)
    
    # Delete the downloaded file
    os.remove(file_path)
    
    # Remove the keyboard
    reply_markup = ReplyKeyboardRemove()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Download complete!", reply_markup=reply_markup)
    
    return ConversationHandler.END

# Handler function for /cancel command
def cancel(update, context):
    message = "Conversation cancelled."
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Set up the ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        TYPE: [MessageHandler(Filters.text, type_handler)],
        QUALITY: [MessageHandler(Filters.text, quality_handler)],
        DOWNLOAD: [MessageHandler(Filters.text, download_handler)],  # Add a new state for download
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
# Add the ConversationHandler to the dispatcher
dispatcher.add_handler(conv_handler)

# Start the bot
updater.start_polling()
updater.idle()
