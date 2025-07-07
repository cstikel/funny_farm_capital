import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Define the sector ETFs to analyze
SECTOR_ETFS = {
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLE': 'Energy',
    'XLF': 'Financials',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLB': 'Materials',
    'XLK': 'Technology',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLC': 'Communication Services'
}

def get_historical_prices(symbol, api_key, months=12):
    """
    Get historical price data from Financial Modeling Prep API
    
    Args:
        symbol (str): The ticker symbol
        api_key (str): FMP API key
        months (int): Number of months of historical data to retrieve
        
    Returns:
        dict: Historical price data
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30+10)  # Add a few extra days for weekends/holidays
    
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'historical' in data and data['historical']:
            return data
        else:
            raise Exception(f"No historical data found for {symbol}")
    else:
        raise Exception(f"Failed to get data for {symbol}. Status code: {response.status_code}")

def calculate_momentum(data, months=3):
    """
    Calculate momentum metrics (total return, risk-adjusted return)
    
    Args:
        data (dict): Historical price data
        months (int): Number of months to calculate momentum for
        
    Returns:
        tuple: (total_return, sharpe_ratio)
    """
    historical = sorted(data['historical'], key=lambda x: x['date'])
    
    # Get prices exactly 12 months apart (or as close as possible)
    if len(historical) < 20:  # Need a minimum amount of data
        raise Exception("Not enough historical data")
    
    newest_price = historical[-1]['close']
    
    # Find price closest to target months ago
    target_date = datetime.strptime(historical[-1]['date'], '%Y-%m-%d') - timedelta(days=months*30)
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    # Find closest date
    date_diffs = [(i, abs((datetime.strptime(x['date'], '%Y-%m-%d') - target_date).days)) 
                 for i, x in enumerate(historical)]
    closest_idx = min(date_diffs, key=lambda x: x[1])[0]
    oldest_price = historical[closest_idx]['close']
    
    # Calculate total return
    total_return = ((newest_price - oldest_price) / oldest_price) * 100
    
    # Calculate volatility (annualized standard deviation of daily returns)
    daily_returns = []
    for i in range(1, len(historical)):
        daily_return = (historical[i]['close'] / historical[i-1]['close']) - 1
        daily_returns.append(daily_return)
    
    volatility = np.std(daily_returns) * np.sqrt(252)  # Annualized volatility
    
    # Calculate Sharpe ratio-like metric (no risk-free rate adjustment)
    sharpe_ratio = (total_return / 100) / volatility if volatility > 0 else 0
    
    return total_return, sharpe_ratio

def analyze_sector_momentum(api_key):
    """
    Analyze momentum across all sectors and identify the strongest one
    
    Args:
        api_key (str): FMP API key
        
    Returns:
        dict: Results of sector momentum analysis
    """
    results = []
    
    print("Analyzing sector momentum...")
    
    for symbol, sector_name in SECTOR_ETFS.items():
        try:
            # Get historical data
            data = get_historical_prices(symbol, api_key)
            
            # Calculate momentum metrics
            total_return, sharpe_ratio = calculate_momentum(data)
            
            # Add to results
            results.append({
                'Symbol': symbol,
                'Sector': sector_name,
                'Return': total_return,
                'Risk-Adjusted Return': sharpe_ratio
            })
            
            print(f"✓ {sector_name} ({symbol}): {total_return:.2f}% return, {sharpe_ratio:.2f} risk-adjusted")
            
        except Exception as e:
            print(f"✗ Error analyzing {sector_name} ({symbol}): {str(e)}")
    
    # Create DataFrame and sort by momentum
    if not results:
        raise Exception("Failed to analyze any sectors")
    
    df = pd.DataFrame(results)
    
    # Sort by total return (primary) and risk-adjusted return (secondary)
    df_return = df.sort_values('Return', ascending=False).reset_index(drop=True)
    df_risk_adjusted = df.sort_values('Risk-Adjusted Return', ascending=False).reset_index(drop=True)
    
    # Get top sectors
    top_return = df_return.iloc[0]
    top_risk_adjusted = df_risk_adjusted.iloc[0]
    
    return {
        'all_sectors': df,
        'top_return': top_return,
        'top_risk_adjusted': top_risk_adjusted
    }

def main():
    print("Sector Momentum Analysis")
    print("========================")
    
    # Replace with your Financial Modeling Prep API key
    API_KEY = "PHaANSXTwW2zC5hpGFO1uhe8EkPXgio7"
    
    try:
        results = analyze_sector_momentum(API_KEY)
        
        # Print results in a nice format
        print("\nResults sorted by Total Return:")
        print(results['all_sectors'].sort_values('Return', ascending=False).to_string(index=False))
        
        print("\nTop sector by Total Return:")
        top = results['top_return']
        print(f"🏆 {top['Sector']} ({top['Symbol']}): {top['Return']:.2f}% return")
        
        print("\nTop sector by Risk-Adjusted Return:")
        top = results['top_risk_adjusted']
        print(f"🏆 {top['Sector']} ({top['Symbol']}): {top['Risk-Adjusted Return']:.2f} risk-adjusted return")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()