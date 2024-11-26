# stock_screener.py
from finvizfinance.screener.overview import Overview
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_trending_symbols(url):
    """Scrape trending symbols from ValueInvestorsClub"""
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to retrieve content: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    trending_header = soup.find('b', string='TRENDING:')

    if not trending_header:
        print("No trending section found.")
        return []

    trending_span = trending_header.find_next('span')
    symbols = []
    
    if trending_span:
        for a_tag in trending_span.find_all('a', href=lambda href: href and href.startswith('/idea/')):
            symbols.append(a_tag.text.strip())

    return symbols

def get_value_stocks(stock_scores):
    """Get value stocks based on fundamental criteria"""
    filters_dict = {
        'Debt/Equity': 'Under 1',
        'Operating Margin': 'Positive (>0%)',
        'P/E': 'Under 20',
        'InsiderTransactions': 'Positive (>0%)'
    }
    
    foverview = Overview()
    foverview.set_filter(filters_dict=filters_dict)
    df_overview = foverview.screener_view()
    tickers = df_overview['Ticker'].to_list()
    
    url = 'https://valueinvestorsclub.com/ideas'
    trending_symbols = get_trending_symbols(url)
    
    value_stocks = list(set(tickers + trending_symbols))
    
    value_scores = stock_scores[stock_scores['ticker'].isin(value_stocks)]
    return value_scores[['ticker', '2023', 'roce_rank', 'coef_rank', 'std_rank', 'final_rank']]

def get_non_value_stocks(stock_scores):
    """Get non-value stocks based on fundamental criteria"""
    filters_dict = {
        'Debt/Equity': 'Over 1',
        'P/E': 'Over 5'
    }
    
    foverview = Overview()
    foverview.set_filter(filters_dict=filters_dict)
    df_overview = foverview.screener_view()
    tickers = df_overview['Ticker'].to_list()
    
    non_value_scores = stock_scores[stock_scores['ticker'].isin(tickers)]
    return non_value_scores[['ticker', '2023', 'roce_rank', 'coef_rank', 'std_rank', 'final_rank']]