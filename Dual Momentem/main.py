import requests
from datetime import datetime, timedelta
import pandas as pd

def get_fmp_data(symbol, api_key):
    """
    Get historical price data from Financial Modeling Prep API
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get data for {symbol}")

def calculate_return(data):
    """
    Calculate 12-month return from historical price data
    """
    historical = data['historical']
    if len(historical) < 2:
        raise Exception("Not enough historical data")
    
    newest_price = historical[0]['close']
    oldest_price = historical[-1]['close']
    return ((newest_price - oldest_price) / oldest_price) * 100

def get_treasury_yield(api_key):
    """
    Get current 1-month Treasury Bill yield as risk-free rate
    """
    url = f"https://financialmodelingprep.com/api/v4/treasury?apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            # Get the most recent 1-month rate
            return float(data[0].get('month1', 0))
    
    raise Exception(f"Failed to get Treasury yield data. Status code: {response.status_code}, Response: {response.text}")


def determine_investment(api_key):
    """
    Determine which investment to choose based on the strategy
    """
    try:
        # Get historical data for all securities
        spy_data = get_fmp_data('SPY', api_key)
        veu_data = get_fmp_data('VEU', api_key)
        
        # Calculate returns
        spy_return = calculate_return(spy_data)
        international_return = calculate_return(veu_data)
        risk_free_return = get_treasury_yield(api_key)
        
        # Print the data for verification
        print(f"SP500 12-month return: {spy_return:.2f}%")
        print(f"International 12-month return: {international_return:.2f}%")
        print(f"Risk-free return: {risk_free_return:.2f}%")
        
        # Apply the investment strategy
        if spy_return - risk_free_return > 0:
            if spy_return > international_return:
                return "SP500 - SPY"
            else:
                return "International - VEU"
        else:
            return "Aggregate Bonds - AGG"
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Replace with your Financial Modeling Prep API key
    API_KEY = "PHaANSXTwW2zC5hpGFO1uhe8EkPXgio7"
    
    result = determine_investment(API_KEY)
    if result:
        print(f"\nRecommended investment: {result}")