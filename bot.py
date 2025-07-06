import os
import logging
from telegram import Update
from telegram.ext import (
    Updater, 
    CommandHandler, 
    CallbackContext,
    PicklePersistence
)
from ebay_helper import EbayHelper
from config import Config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class EbayBot:
    def __init__(self):
        self.persistence = PicklePersistence(filename='bot_data')
        self.updater = Updater(
            token=Config.TELEGRAM_TOKEN,
            persistence=self.persistence,
            use_context=True
        )
        self.dispatcher = self.updater.dispatcher
        
        # Register handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("active", self.active_listings))
        self.dispatcher.add_handler(CommandHandler("help", self.help))
        
        # Store chat ID if provided in config
        if Config.CHAT_ID:
            self.updater.bot_data['chat_id'] = Config.CHAT_ID

    def start(self, update: Update, context: CallbackContext):
        """Send a message when the command /start is issued."""
        chat_id = update.message.chat_id
        context.bot_data['chat_id'] = chat_id
        update.message.reply_text(
            'Ebay Listing Bot activated!\n'
            'Use /active to see your current listings\n'
            f'Your chat ID {chat_id} has been stored.'
        )

    def active_listings(self, update: Update, context: CallbackContext):
        """Send a message with active listings when /active is issued."""
        listings = EbayHelper.get_active_listings()
        
        if not listings:
            update.message.reply_text("Couldn't fetch active listings at this time.")
            return
        
        message = "📋 Your Active Listings:\n\n"
        for item in listings[:10]:  # Limit to 10 for readability
            details = EbayHelper.get_listing_details(item['sku'])
            title = details.get('product', {}).get('title', 'No title')
            message += f"📦 {item['sku']} - {title}\n"
            if 'price' in details:
                message += f"   💰 Price: {details['price']}\n"
        
        update.message.reply_text(message)

    def help(self, update: Update, context: CallbackContext):
        """Send a help message."""
        update.message.reply_text(
            'Available commands:\n'
            '/start - Initialize the bot\n'
            '/active - Show active listings\n'
            '/help - Show this help message'
        )

    def run(self):
        """Start the bot."""
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    bot = EbayBot()
    bot.run()
