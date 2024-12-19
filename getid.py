

from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram.request import HTTPXRequest

BOT_TOKEN = "7015840155:AAH4AfB2qSKZFLQMil7UNXJWCo9prM_CNyM"

async def get_channel_id(update, context):
    # Check if the update is from a channel
    if update.channel_post:
        channel_id = update.channel_post.chat_id
        print(f"Channel ID: {channel_id}")
    else:
        print("This is not a channel message.")

if __name__ == "__main__":
    # Configure HTTPXRequest for timeouts
    request = HTTPXRequest(connect_timeout=20, read_timeout=30)

    # Initialize bot application
    application = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    # Add a handler for channel posts
    application.add_handler(MessageHandler(filters.ALL, get_channel_id))

    # Start the bot
    application.run_polling()
