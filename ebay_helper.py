import requests
from config import Config

class EbayHelper:
    @staticmethod
    def get_active_listings():
        url = "https://api.ebay.com/sell/inventory/v1/inventory_item"
        headers = {
            "Authorization": f"Bearer {Config.EBAY_AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get('inventoryItems', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching active listings: {e}")
            return None

    @staticmethod
    def get_listing_details(item_id):
        url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{item_id}"
        headers = {
            "Authorization": f"Bearer {Config.EBAY_AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching listing details: {e}")
            return None
