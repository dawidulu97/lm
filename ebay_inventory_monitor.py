import asyncio
import feedparser
from datetime import datetime, timezone
from telegram import Bot
from telegram.ext import Application
import os
import logging
from collections import defaultdict
from aiohttp import web

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
        self.port = int(os.getenv('PORT', 10000))
        
        # Tracking state
        self.known_items = defaultdict(dict)
        self.current_inventory = []
        self.app = None
        self.bot_app = None

    async def send_telegram_message(self, message, disable_preview=True):
        """Send message to Telegram with error handling"""
        try:
            await self.bot_app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                disable_web_page_preview=disable_preview
            )
            logger.info("Telegram message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def health_check(self, request):
        """Health check endpoint for Render"""
        return web.Response(text="OK")

    async def start_web_server(self):
        """Start a simple web server for port binding"""
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Web server started on port {self.port}")

    async def get_current_listings(self):
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

    async def send_current_inventory(self):
        """Send current inventory at startup"""
        current_items = await self.get_current_listings()
        if not current_items:
            await self.send_telegram_message("⚠️ Could not fetch current listings")
            return

        message = f"📋 Current listings from {self.seller_name} (showing 10 of {len(current_items)}):\n\n"
        for item in current_items[:10]:
            message += (
                f"🏷 {item['title']}\n"
                f"💰 {item['price']}\n"
                f"⏰ {item['time']}\n"
                f"🔗 {item['link']}\n\n"
            )
        
        if len(current_items) > 10:
            message += f"➕ {len(current_items)-10} more items not shown\n"
        
        await self.send_telegram_message(message)

    async def check_new_listings(self, context):
        """Check for new listings (callback for job queue)"""
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
                for item in new_items[:5]:
                    message += (
                        f"📌 {item['title']}\n"
                        f"💰 {item['price']}\n"
                        f"⏰ {item['time']}\n"
                        f"🔗 {item['link']}\n\n"
                    )
                await self.send_telegram_message(message.strip())
                
        except Exception as e:
            logger.error(f"Error checking new listings: {e}")

    async def startup(self, application):
        """Run startup tasks"""
        await self.send_telegram_message(
            f"🟢 eBay Listings Monitor Started!\n"
            f"• Seller: {self.seller_name}\n"
            f"• Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"• Checking every {self.poll_interval//60} minutes"
        )
        await self.send_current_inventory()
        application.job_queue.run_repeating(
            self.check_new_listings,
            interval=self.poll_interval,
            first=10
        )

    async def run(self):
        """Main application runner"""
        # Create Telegram application
        self.bot_app = Application.builder().token(self.telegram_token).build()
        
        # Add startup handler
        self.bot_app.add_handler(
            type("StartupHandler", (), {
                "check_update": lambda _: None,
                "handle_update": lambda _, __: None
            })()
        )
        self.bot_app.post_init = self.startup
        
        # Start web server and bot
        await asyncio.gather(
            self.start_web_server(),
            self.bot_app.run_polling()
        )

if __name__ == "__main__":
    # Verify required environment variables
    required_vars = ['TELEGRAM_TOKEN', 'CHAT_ID', 'SELLER_USERNAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    monitor = EBayInventoryMonitor()
    
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
