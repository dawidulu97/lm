import feedparser
import time
from datetime import datetime, timezone
from telegram import Bot
import os
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EBayInventoryMonitor:
    def __init__(self):
        # Configuration
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('CHAT_ID')
        self.seller_name = os.getenv('SELLER_USERNAME')
        self.poll_interval = 900  # 15 minutes
        
        # Tracking state
        self.known_items = defaultdict(dict)
        self.bot = Bot(token=self.telegram_token)

    def send_telegram_message(self, message):
        """Send message to Telegram with error handling"""
        try:
            self.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info("Telegram message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def get_current_listings(self):
        """Get all current listings from RSS feed"""
        try:
            feed = feedparser.parse(f"https://www.ebay.com/sch/{self.seller_name}/m.html?_rss=1&_sop=10")
            current_items = []
            
            for entry in feed.entries[:50]:  # Get first 50 listings
                item_id = entry.link.split('/')[-1].split('?')[0]
                current_items.append({
                    'id': item_id,
                    'title': entry.title,
                    'price': entry.get('ev_price', 'N/A'),
                    'link': entry.link,
                    'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                })
                self.known_items[item_id] = current_items[-1]
            
            logger.info(f"Found {len(current_items)} current listings")
            return current_items
            
        except Exception as e:
            logger.error(f"Error fetching current listings: {e}")
            return []

    def check_new_listings(self):
        """Check for new listings"""
        try:
            feed = feedparser.parse(f"https://www.ebay.com/sch/{self.seller_name}/m.html?_rss=1&_sop=10")
            new_items = []
            
            for entry in feed.entries:
                item_id = entry.link.split('/')[-1].split('?')[0]
                if item_id not in self.known_items:
                    new_items.append({
                        'id': item_id,
                        'title': entry.title,
                        'price': entry.get('ev_price', 'N/A'),
                        'link': entry.link,
                        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                    })
                    self.known_items[item_id] = new_items[-1]
            
            if new_items:
                message = f"🆕 New listings from {self.seller_name}:\n\n"
                for item in new_items[:5]:  # Limit to 5 items
                    message += (
                        f"📌 {item['title']}\n"
                        f"💰 {item['price']}\n"
                        f"⏰ {item['time']}\n"
                        f"🔗 {item['link']}\n\n"
                    )
                self.send_telegram_message(message.strip())
                
        except Exception as e:
            logger.error(f"Error checking new listings: {e}")

    def run(self):
        """Main monitoring loop"""
        # Send startup message
        self.send_telegram_message(
            f"🟢 eBay Listings Monitor Started!\n"
            f"• Seller: {self.seller_name}\n"
            f"• Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"• Checking every {self.poll_interval//60} minutes"
        )
        
        # Initial inventory check
        current_items = self.get_current_listings()
        if current_items:
            message = f"📋 Current listings from {self.seller_name} (showing 10 of {len(current_items)}):\n\n"
            for item in current_items[:10]:
                message += (
                    f"🏷 {item['title']}\n"
                    f"💰 {item['price']}\n"
                    f"⏰ {item['time']}\n"
                    f"🔗 {item['link']}\n\n"
                )
            self.send_telegram_message(message)
        
        # Continuous monitoring
        logger.info("Starting monitoring loop...")
        while True:
            try:
                self.check_new_listings()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(300)  # Wait 5 minutes after error

if __name__ == "__main__":
    # Verify required environment variables
    required_vars = ['TELEGRAM_TOKEN', 'CHAT_ID', 'SELLER_USERNAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    try:
        EBayInventoryMonitor().run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
