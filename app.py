# Workaround for Python 3.13 missing imghdr
import sys
import warnings
from unittest.mock import MagicMock

if sys.version_info >= (3, 13):
    sys.modules['imghdr'] = MagicMock()
    warnings.warn("imghdr workaround applied for Python 3.13")

# Rest of your imports...
from flask import Flask, jsonify
from bot import EbayBot

import threading

app = Flask(__name__)

# Run the bot in a separate thread
def run_bot():
    bot = EbayBot()
    bot.run()

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Ebay Listing Update Bot"
    })

if __name__ == '__main__':
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000)
