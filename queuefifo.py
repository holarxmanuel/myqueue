import sqlite3
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder
import logging
import time

BOT_TOKEN = "7015840155:AAH4AfB2qSKZFLQMil7UNXJWCo9prM_CNyM"
SOURCE_CHANNEL_ID = -1002345834202  # Source Channel ID
RECIPIENT_CHANNEL_ID = -1002497200409  # Recipient Channel ID
MAX_MESSAGES_PER_DAY = 3  # Max messages to forward per day

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize the database
def init_db():
    conn = sqlite3.connect("forwarding.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_messages (
            message_id INTEGER PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS last_processed (
            id INTEGER PRIMARY KEY,
            message_id INTEGER,
            last_forwarded_timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Get the last processed message ID and timestamp
def get_last_processed_message():
    conn = sqlite3.connect("forwarding.db")
    c = conn.cursor()
    c.execute("SELECT message_id, last_forwarded_timestamp FROM last_processed WHERE id = 1")
    result = c.fetchone()
    conn.close()
    return result

# Update the last processed message ID and timestamp
def update_last_processed_message(message_id, timestamp):
    conn = sqlite3.connect("forwarding.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO last_processed (id, message_id, last_forwarded_timestamp) VALUES (1, ?, ?)", (message_id, timestamp))
    conn.commit()
    conn.close()

# Check if the message has already been forwarded
def is_message_forwarded(message_id):
    conn = sqlite3.connect("forwarding.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM forwarded_messages WHERE message_id = ?", (message_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Mark a message as forwarded
def mark_message_forwarded(message_id):
    conn = sqlite3.connect("forwarding.db")
    c = conn.cursor()
    c.execute("INSERT INTO forwarded_messages (message_id) VALUES (?)", (message_id,))
    conn.commit()
    conn.close()

# Send a new message from the bot without quoting the sender
async def send_message_as_bot(bot: Bot, message):
    try:
        if message.text:
            await bot.send_message(RECIPIENT_CHANNEL_ID, message.text)
        elif message.photo:
            await bot.send_photo(RECIPIENT_CHANNEL_ID, message.photo[-1].file_id)
        elif message.video:
            await bot.send_video(RECIPIENT_CHANNEL_ID, message.video.file_id)
        else:
            logger.info("Unsupported message type")
    except TelegramError as e:
        logger.error(f"Error while sending message: {e}")

# Forward all unprocessed messages
async def forward_all_messages(bot: Bot):
    try:
        # Get the last processed message ID and timestamp
        last_processed_message, last_forwarded_timestamp = get_last_processed_message()

        # Fetch messages from the source channel
        offset = last_processed_message + 1 if last_processed_message else None
        updates = await bot.get_updates(offset=offset, timeout=60)
        sent_count = 0
        current_timestamp = int(time.time())

        # If more than 24 hours have passed since the last forward, reset sent_count
        if last_forwarded_timestamp and current_timestamp - last_forwarded_timestamp > 86400:
            sent_count = 0

        for update in updates:
            message = update.channel_post  # Use channel_post instead of message
            if message and message.chat.id == SOURCE_CHANNEL_ID:
                # Print message info
                print(f"Fetched message ID: {message.message_id}, Type: {message.text or 'Image/Video'}")

                if not is_message_forwarded(message.message_id):
                    # Send the message as a new message from the bot (no quote)
                    print(f"Sending message ID: {message.message_id}")
                    await send_message_as_bot(bot, message)

                    # Mark the message as forwarded
                    mark_message_forwarded(message.message_id)

                    # Update the last processed message ID and timestamp
                    update_last_processed_message(message.message_id, current_timestamp)

                    sent_count += 1

                # Stop if we have sent 3 messages in the 24-hour period
                if sent_count >= MAX_MESSAGES_PER_DAY:
                    break
    except TelegramError as e:
        logger.error(f"Error while processing messages: {e}")

async def main():
    init_db()
    application = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(60).read_timeout(120).build()
    bot = application.bot
    # Run the forwarding logic for all messages
    await forward_all_messages(bot)
    logger.info("Real-time test completed. Check the recipient channel for sent messages.")

if __name__ == "__main__":
    asyncio.run(main())
