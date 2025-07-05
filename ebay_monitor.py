import os
import time
import logging
import schedule
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from ebay_rest import API, DateTime, Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EBaySellerMonitor:
    def __init__(self):
        # Load configuration from environment variables
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('CHAT_ID')
        self.seller_username = os.getenv('SELLER_USERNAME')
        
        # eBay API credentials
        ebay_app_id = os.getenv('EBAY_APP_ID')
        ebay_cert_id = os.getenv('EBAY_CERT_ID')
        ebay_dev_id = os.getenv('EBAY_DEV_ID')
        
        self.last_check_time = None
        self.known_items = set()
        
        # Initialize Telegram bot
        self.telegram_bot = Bot(token=self.telegram_token) if self.telegram_token else None
        
        # Initialize eBay API
        try:
            self.ebay_api = API(
                application_id=ebay_app_id,
                certification_id=ebay_cert_id,
                dev_id=ebay_dev_id
            )
            logger.info("eBay API initialized successfully")
        except Error as e:
            logger.error(f"Failed to initialize eBay API: {e}")
            raise

    def validate_config(self):
        """Validate all required configuration is present"""
        required_vars = {
            'TELEGRAM_TOKEN': self.telegram_token,
            'CHAT_ID': self.chat_id,
            'EBAY_APP_ID': os.getenv('EBAY_APP_ID'),
            'EBAY_CERT_ID': os.getenv('EBAY_CERT_ID'),
            'EBAY_DEV_ID': os.getenv('EBAY_DEV_ID'),
            'SELLER_USERNAME': self.seller_username
        }
        
        missing = [var for var, val in required_vars.items() if not val]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    def send_telegram_message(self, message):
        """Send message to Telegram with error handling"""
        if not self.telegram_bot:
            logger.warning("Telegram bot not initialized - skipping message")
            return
            
        try:
            self.telegram_bot.send_message(chat_id=self.chat_id, text=message)
            logger.info("Telegram message sent successfully")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def get_new_items(self):
        """Fetch new items from eBay seller"""
        try:
            params = {
                'seller_username': self.seller_username,
                'sort': 'StartTimeNewest',
                'limit': 20  # Get most recent 20 items
            }
            
            if self.last_check_time:
                params['StartTimeFrom'] = self.last_check_time
            
            logger.info(f"Fetching items with params: {params}")
            response = self.ebay_api.buy_browse_search(params=params)
            items = response.get('itemSummaries', [])
            
            new_items = []
            for item in items:
                item_id = item['itemId']
                if item_id not in self.known_items:
                    self.known_items.add(item_id)
                    new_items.append(item)
            
            logger.info(f"Found {len(new_items)} new items")
            return new_items
            
        except Error as e:
            logger.error(f"Error fetching eBay items: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_new_items: {e}")
            return []

    def format_item_message(self, item):
        """Format an item into a readable message"""
        title = item.get('title', 'No title')
        price = item.get('price', {}).get('value', 'N/A')
        currency = item.get('price', {}).get('currency', '')
        url = item.get('itemWebUrl', '')
        
        return (
            f"📌 {title}\n"
            f"💰 Price: {price} {currency}\n"
            f"🔗 {url}"
        )

    def check_for_new_listings(self):
        """Check for and notify about new listings"""
        logger.info("Starting check for new listings")
        
        new_items = self.get_new_items()
        
        if new_items:
            message = f"🎉 New items listed by {self.seller_username}:\n\n"
            for item in new_items[:5]:  # Limit to 5 items per message
                message += self.format_item_message(item) + "\n\n"
            
            # Send notification
            self.send_telegram_message(message.strip())
        
        # Update last check time (UTC)
        self.last_check_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
        logger.info(f"Check completed at {self.last_check_time}")

    def run(self):
        """Main execution loop"""
        try:
            self.validate_config()
            
            # Send startup message
            startup_msg = (
                f"🟢 eBay Seller Monitor Started!\n"
                f"• Monitoring: {self.seller_username}\n"
                f"• Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"• Environment: {os.getenv('RENDER', 'Not Render')}"
            )
            self.send_telegram_message(startup_msg)
            logger.info("Startup message sent")
            
            # Initial check
            self.check_for_new_listings()
            
            # Schedule regular checks (every 30 minutes)
            schedule.every(30).minutes.do(self.check_for_new_listings)
            
            logger.info("Bot is running. Monitoring for new listings...")
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except Exception as e:
            error_msg = f"❌ Bot crashed: {str(e)}"
            self.send_telegram_message(error_msg)
            logger.critical(error_msg, exc_info=True)
            raise

if __name__ == "__main__":
    try:
        monitor = EBaySellerMonitor()
        monitor.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        exit(1)
