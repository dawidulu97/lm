import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Ebay
    EBAY_APP_ID = os.getenv('EBAY_APP_ID')
    EBAY_CERT_ID = os.getenv('EBAY_CERT_ID')
    EBAY_DEV_ID = os.getenv('EBAY_DEV_ID')
    EBAY_AUTH_TOKEN = os.getenv('EBAY_AUTH_TOKEN')
    EBAY_REFRESH_TOKEN = os.getenv('EBAY_REFRESH_TOKEN')
    
    # Other
    POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '300'))  # 5 minutes default
