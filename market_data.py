# market_data.py
from finvizfinance.quote import finvizfinance

def str_to_num(input):
    """Convert percentage string to float"""
    return float(input.strip('%')) / 100

def invest_market(input):
    """Determine if market is investable based on indicator"""
    return "Investable" if input > 0 else "Avoid"

def get_market_analysis():
    """Get market analysis for major indexes"""
    indexes = ['DJIA', 'QQQ', 'SPY', 'IWM']
    market_data = []
    
    intervals = {
        'Near  - 1 Month': 'SMA20',
        'Med   - 3 Month': 'SMA50',
        'Long  - 1 Year ': 'SMA200'
    }
    
    for ind in indexes:
        index_data = [f'Index: {ind}']
        stock = finvizfinance(ind)
        stock_fundament = stock.ticker_fundament()
        for interval, level in intervals.items():
            avoid = invest_market(str_to_num(stock_fundament[level]))
            index_data.append(f'  {interval} ------- {avoid}')
        market_data.extend(index_data)
        market_data.append("")
        
    return market_data
