import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time

# Import the sector momentum analysis functions
from sector_momentum import SECTOR_ETFS, get_historical_prices, calculate_momentum, analyze_sector_momentum

# Define the ETF constituents API endpoint
ETF_CONSTITUENTS_ENDPOINT = "https://financialmodelingprep.com/api/v3/etf-holder/"

# Define sectors and their corresponding ETFs
SECTOR_TO_ETF = {v: k for k, v in SECTOR_ETFS.items()}

def get_etf_constituents(etf_symbol, api_key):
    """
    Get the constituent stocks of an ETF
    
    Args:
        etf_symbol (str): The ETF ticker symbol
        api_key (str): FMP API key
        
    Returns:
        list: List of constituent stock data
    """
    url = f"{ETF_CONSTITUENTS_ENDPOINT}{etf_symbol}?apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data:
            return data
        else:
            raise Exception(f"No constituent data found for {etf_symbol}")
    else:
        raise Exception(f"Failed to get constituents for {etf_symbol}. Status code: {response.status_code}")

def analyze_top_stocks_in_sectors(top_sectors, api_key, max_stocks_per_sector=10):
    """
    Analyze top momentum stocks within the specified sectors
    
    Args:
        top_sectors (list): List of sector names
        api_key (str): FMP API key
        max_stocks_per_sector (int): Maximum number of stocks to analyze per sector
        
    Returns:
        dict: Results with top stocks per sector
    """
    results = {}
    
    for sector in top_sectors:
        print(f"\nAnalyzing stocks in {sector} sector...")
        
        # Get the corresponding ETF symbol
        etf_symbol = SECTOR_TO_ETF.get(sector)
        if not etf_symbol:
            print(f"Error: Could not find ETF for sector {sector}")
            continue
            
        try:
            # Get ETF constituents
            constituents = get_etf_constituents(etf_symbol, api_key)
            
            # Sort by weight (descending) and take top stocks
            sorted_constituents = sorted(constituents, key=lambda x: float(x.get('weight', 0)), reverse=True)
            top_constituents = sorted_constituents[:50]  # Take top 50 by weight to analyze momentum
            
            # Analyze momentum for each constituent
            stock_results = []
            count = 0
            
            for stock in top_constituents:
                symbol = stock.get('asset')
                
                # Skip if no symbol
                if not symbol:
                    continue
                    
                try:
                    # Get historical prices
                    stock_data = get_historical_prices(symbol, api_key)
                    
                    # Calculate momentum - change what the time frame is? Book suggested 12 at high-level, but should we do lower level for stocks
                    total_return, sharpe_ratio = calculate_momentum(stock_data, months=3)
                    
                    # Add to results
                    stock_results.append({
                        'Symbol': symbol,
                        'Name': stock.get('name', ''),
                        'Weight': float(stock.get('weight', 0)),
                        'Return': total_return,
                        'Risk-Adjusted': sharpe_ratio
                    })
                    
                    print(f"  ✓ {symbol}: {total_return:.2f}% return")
                    
                    # Add a small delay to avoid API rate limits
                    time.sleep(0.2)
                    
                    # Increment counter
                    count += 1
                    if count >= max_stocks_per_sector:
                        break
                        
                except Exception as e:
                    print(f"  ✗ Error analyzing {symbol}: {str(e)}")
            
            # Sort results by total return
            if stock_results:
                stock_df = pd.DataFrame(stock_results)
                stock_df_sorted = stock_df.sort_values('Return', ascending=False).reset_index(drop=True)
                results[sector] = stock_df_sorted
            else:
                print(f"Could not find any valid stocks for {sector}")
                
        except Exception as e:
            print(f"Error analyzing {sector} sector: {str(e)}")
    
    return results

def main():
    print("Top Momentum Stocks in Leading Sectors")
    print("======================================")
    
    API_KEY = "PHaANSXTwW2zC5hpGFO1uhe8EkPXgio7"
    
    try:
        # First, find the top sectors
        sector_results = analyze_sector_momentum(API_KEY)
        sector_df = sector_results['all_sectors']
        
        # Get top 2 sectors by return
        top_sectors = sector_df.sort_values('Return', ascending=False).head(2)['Sector'].tolist()
        
        print(f"\nAnalyzing stocks in top 2 sectors: {', '.join(top_sectors)}")
        
        # Find top stocks in those sectors
        stock_results = analyze_top_stocks_in_sectors(top_sectors, API_KEY, max_stocks_per_sector=10)
        
        # Display results
        for sector, stocks_df in stock_results.items():
            print(f"\nTop momentum stocks in {sector} sector:")
            print(stocks_df[['Symbol', 'Name', 'Return', 'Risk-Adjusted']].head(10).to_string(index=False))
            
            # Highlight the very top stock
            if not stocks_df.empty:
                top_stock = stocks_df.iloc[0]
                print(f"\n🏆 Top stock in {sector}: {top_stock['Symbol']} ({top_stock['Name']})")
                print(f"   Return: {top_stock['Return']:.2f}%")
                print(f"   Risk-Adjusted Return: {top_stock['Risk-Adjusted']:.2f}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()