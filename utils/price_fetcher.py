# price_fetcher.py
import certifi
import json
from urllib.request import urlopen

def get_jsonparsed_data(url):
    """Parse JSON data from URL"""
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    return json.loads(data)
    
def get_price(tick):
    """Get current price for a ticker"""
    url = (f"https://financialmodelingprep.com/api/v3/quote/{tick}?apikey=PHaANSXTwW2zC5hpGFO1uhe8EkPXgio7")
    data = get_jsonparsed_data(url)
    price = data[0]['price']
    return price