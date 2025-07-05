import feedparser
import time
from datetime import datetime, timedelta
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
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '900'))  # Default 15 minutes
        
        # Tracking state
        self.known_items = defaultdict(dict)  # {item_id: {title, price, link, time}}
        self.current_inventory = []
        self.bot = Bot(token=self.telegram_token) if self.telegram_token else None
        
        # RSS URL for seller's listings sorted by newest first
        self.rss_url = f"https://www.ebay.com/sch/{self.seller_name}/m.html?_rss=1&_sop=10"

    def fetch_current_inventory(self):
        """Get all current listings when bot starts"""
        try:
            feed = feedparser.parse(self.rss_url)
            self.current_inventory = []
            
            for entry in feed.entries[:50]:  # Get top 50 current listings
                item_id = entry.link.split('/')[-1].split('?')[0]  # Extract item ID from URL
                self.known_items[item_id] = {
                    'title': entry.title,
                    'price': entry.get('ev_price', 'N/A'),
                    'link': entry.link,
                    'time': datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d %H:%M:%S UTC')
                }
                self.current_inventory.append(self.known_items[item_id])
            
            logger.info(f"Found {len(self.current_inventory)} current listings")
            return True
        except Exception as e:
            logger.error(f"Error fetching inventory: {e}")
            return False

    def get_new_items(self):
        """Check for items not seen before"""
        try:
            feed = feedparser.parse(self.rss_url)
            new_items = []
            
            for entry in feed.entries[:20]:  # Check most recent 20 listings
                item_id = entry.link.split('/')[-1].split('?')[0]
                if item_id not in self.known_items:
                    listing_time = datetime(*entry.published_parsed[:6])
                    new_item = {
                        'title': entry.title,
                        'price': entry.get('ev_price', 'N/A'),
                        'link': entry.link,
                        'time': listing_time.strftime('%Y-%m-%d %H:%M:%S UTC')
                    }
                    self.known_items[item_id] = new_item
                    new_items.append(new_item)
                    logger.info(f"New item detected: {entry.title}")
            
            return new_items
            
        except Exception as e:
            logger.error(f"Error checking for new items: {e}")
            return []

    def send_telegram_message(self, message, disable_preview=True):
        """Send message to Telegram with error handling"""
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                disable_web_page_preview=disable_preview
            )
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    def format_inventory_message(self, inventory):
        """Format current inventory for Telegram"""
        message = f"📋 Current Inventory for {self.seller_name} ({len(inventory)} items):\n\n"
        for item in inventory[:10]:  # Show top 10 items
            message += f"🏷 {item['title']}\n💰 {item['price']}\n⏰ {item['time']}\n🔗 {item['link']}\n\n"
        
        if len(inventory) > 10:
            message += f"➕ {len(inventory)-10} more items not shown\n"
        
        return message

    def format_new_items_message(self, new_items):
        """Format new listings alert"""
        message = f"🆕 {len(new_items)} New Listing(s) from {self.seller_name}:\n\n"
        for item in new_items:
            message += f"🏷 {item['title']}\n💰 {item['price']}\n⏰ {item['time']}\n🔗 {item['link']}\n\n"
        return message

    def run(self):
        """Main execution loop"""
        # Initial inventory scan
        if not self.fetch_current_inventory():
            logger.error("Failed initial inventory scan")
            return

        # Send initial inventory report
        self.send_telegram_message(
            f"🟢 eBay Inventory Monitor Started!\n"
            f"• Seller: {self.seller_name}\n"
            f"• Current items: {len(self.current_inventory)}\n"
            f"• Checking every {self.poll_interval//60} minutes\n\n" +
            self.format_inventory_message(self.current_inventory)
        )

        # Monitoring loop
        logger.info("Starting monitoring loop...")
        while True:
            try:
                new_items = self.get_new_items()
                if new_items:
                    self.send_telegram_message(self.format_new_items_message(new_items))
                
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
