import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def analyze_portfolio_positions(portfolio_file: str, exclude_stocks: list = None, negative_weight: float = 10) -> tuple:
    """Analyze portfolio positions and calculate required cash adjustments"""
    if exclude_stocks is None:
        exclude_stocks = []
        
    # Read current portfolio
    current_portfolio = pd.read_csv(portfolio_file, skiprows=3)
    current_portfolio = current_portfolio[current_portfolio['Security Type'] == 'Equity']
    
    # Calculate current position sizes and total value
    current_portfolio['Mkt Val (Market Value)'] = pd.to_numeric(
        current_portfolio['Mkt Val (Market Value)'].str.replace('$', '').str.replace(',', ''), 
        errors='coerce'
    )
    
    # Remove excluded stocks from optimization calculation
    optimize_portfolio = current_portfolio[~current_portfolio['Symbol'].isin(exclude_stocks)].copy()
    excluded_portfolio = current_portfolio[current_portfolio['Symbol'].isin(exclude_stocks)].copy()
    
    # Calculate total portfolio value and adjust for optimization
    total_value = current_portfolio['Mkt Val (Market Value)'].sum()
    optimize_value = optimize_portfolio['Mkt Val (Market Value)'].sum()
    
    # Calculate current percentages for optimized portion
    optimize_portfolio['current_percent'] = (optimize_portfolio['Mkt Val (Market Value)'] / total_value * 100).round(0)
    
    # Get stock data and calculate volatility-based weights
    results = []
    start_date = '2024-10-10'
    end_date = '2024-11-09'
    
    for ticker in optimize_portfolio['Symbol']:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if not hist.empty:
                hist['day_range'] = ((hist['High'] - hist['Low']) / hist['Open']).round(4)
                hist['day_change'] = hist['Close'] - hist['Open']
                hist['weighted_var'] = np.where(
                    hist['day_change'] < 0,
                    hist['day_range'] * negative_weight,
                    hist['day_range']
                )
                
                avg_variance = hist['weighted_var'].mean()
                results.append({'ticker': ticker, 'variance': avg_variance})
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue
    
    # Calculate variance-based weights
    variance_df = pd.DataFrame(results)
    total_variance = variance_df['variance'].sum()
    variance_df['pct_variance'] = variance_df['variance'] / total_variance
    variance_df['ideal_variance'] = 1 / len(variance_df)
    
    # Calculate update size
    variance_df['update_size'] = variance_df['ideal_variance'] / variance_df['pct_variance']
    temp_update_sum = variance_df['update_size'].sum()
    
    # Calculate ideal percentages for optimized portion only
    optimize_total_pct = optimize_portfolio['current_percent'].sum()
    variance_df['ideal_percent'] = (variance_df['update_size'] / temp_update_sum * optimize_total_pct).round(0)
    
    # Create output dataframe for optimized stocks
    output_df = optimize_portfolio[['Symbol', 'current_percent']].merge(
        variance_df[['ticker', 'ideal_percent']], 
        left_on='Symbol', 
        right_on='ticker',
        how='left'
    )
    
    # Calculate cash changes
    output_df['cash_change'] = ((output_df['ideal_percent'] - output_df['current_percent']) / 100 * total_value).round(0)
    
    # Adjust final stock to ensure zero sum
    total_change = output_df['cash_change'].sum()
    if not output_df.empty:
        last_idx = output_df.index[-1]
        output_df.loc[last_idx, 'cash_change'] -= total_change
        output_df.loc[last_idx, 'ideal_percent'] = (
            output_df.loc[last_idx, 'current_percent'] + 
            (output_df.loc[last_idx, 'cash_change'] / total_value * 100)
        ).round(0)
    
    # Calculate Sharpe improvement
    current_std = output_df['current_percent'].std()
    ideal_std = output_df['ideal_percent'].std()
    sharpe_improvement = ((1/ideal_std) / (1/current_std) - 1) * 100
    
    # Sort by cash change
    output_df = output_df[['Symbol', 'current_percent', 'ideal_percent', 'cash_change']]
    output_df = output_df.sort_values('cash_change', ascending=False)
    
    return output_df, sharpe_improvement, total_value, current_portfolio