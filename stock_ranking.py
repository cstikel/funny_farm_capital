import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time
from tqdm import tqdm
from scipy import stats

class StockAnalyzer:
    def __init__(self, api_key, base_url="https://financialmodelingprep.com/api/v3"):
        self.api_key = api_key
        self.base_url = base_url
        self.retries = 10

    def _make_request(self, endpoint, params):
        for attempt in range(self.retries):
            try:
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if "Too many requests" in str(e):
                    print(f"\nRate limit hit. Waiting 30 seconds... (Attempt {attempt + 1}/{self.retries})")
                    time.sleep(30)
                    continue
                raise
        return []

    def get_market_cap_stocks(self, limit=1000):
        endpoint = f"{self.base_url}/stock-screener"
        params = {
            'apikey': self.api_key,
            'limit': limit,
            'country': 'US',
            'exchange': 'NYSE,NASDAQ',
            'isEtf': 'false',
            'isActivelyTrading': 'true'
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            df = pd.DataFrame(response.json())
            df = df[~df['symbol'].str.contains(r'\.|:', na=False)]
            return df
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def _get_income_statement(self, symbol: str, period='annual'):
        endpoint = f"{self.base_url}/income-statement/{symbol}"
        params = {'apikey': self.api_key, 'period': period}
        return self._make_request(endpoint, params)

    def _get_balance_sheet(self, symbol: str, period='annual'):
        endpoint = f"{self.base_url}/balance-sheet-statement/{symbol}"
        params = {'apikey': self.api_key, 'period': period}
        return self._make_request(endpoint, params)

    def get_yearly_metrics(self, symbol: str, years: int = 10):
        try:
            ttm_income = self._get_income_statement(symbol, period='quarter')
            ttm_balance = self._get_balance_sheet(symbol, period='quarter')
            
            if not ttm_income or not ttm_balance:
                return {}
            
            ttm_income = ttm_income[:4]
            ttm_balance = ttm_balance[0] if ttm_balance else {}
            
            income_stmt = self._get_income_statement(symbol)
            balance_sheet = self._get_balance_sheet(symbol)
            
            metrics = {}
            current_year = datetime.now().year
            
            if ttm_income and ttm_balance:
                ttm_ebit = sum(q.get('operatingIncome', 0) for q in ttm_income)
                ttm_revenue = sum(q.get('revenue', 0) for q in ttm_income)
                ttm_capital = (ttm_balance.get('totalAssets', 0) - 
                             ttm_balance.get('totalCurrentLiabilities', 0))
                
                if ttm_capital and ttm_revenue:
                    metrics[f'roce_{current_year}'] = ttm_ebit / ttm_capital
                    metrics[f'operating_margin_{current_year}'] = ttm_ebit / ttm_revenue
                    
                    last_year_revenue = income_stmt[0].get('revenue') if income_stmt else None
                    if last_year_revenue:
                        metrics[f'revenue_growth_{current_year}'] = ((ttm_revenue - last_year_revenue) / last_year_revenue)

            for year in range(current_year - years, current_year):
                year_data = next((x for x in income_stmt if x['date'].startswith(str(year))), {})
                balance_data = next((x for x in balance_sheet if x['date'].startswith(str(year))), {})
                
                if year_data and balance_data:
                    ebit = year_data.get('operatingIncome')
                    capital_employed = (balance_data.get('totalAssets', 0) - 
                                     balance_data.get('totalCurrentLiabilities', 0))
                    revenue = year_data.get('revenue')
                    
                    if capital_employed and revenue and ebit:
                        metrics[f'roce_{year}'] = ebit / capital_employed
                        metrics[f'operating_margin_{year}'] = ebit / revenue
                        
                        prev_year_data = next((x for x in income_stmt if x['date'].startswith(str(year-1))), {})
                        prev_revenue = prev_year_data.get('revenue')
                        if prev_revenue and revenue:
                            metrics[f'revenue_growth_{year}'] = ((revenue - prev_revenue) / prev_revenue)
            
            return metrics
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            return {}

    def analyze_stocks(self, limit=1000, weights=None):
        base_df = self.get_market_cap_stocks(limit)
        if base_df.empty:
            return pd.DataFrame()

        metrics_data = []
        pbar = tqdm(total=len(base_df), desc="Processing stocks")
        
        for _, row in base_df.iterrows():
            metrics = self.get_yearly_metrics(row['symbol'])
            metrics_data.append(metrics)
            time.sleep(0.25)
            pbar.update(1)
        
        pbar.close()
        
        metrics_df = pd.DataFrame(metrics_data)
        df = pd.concat([base_df, metrics_df], axis=1)
        
        year_columns = [col for col in metrics_df.columns]
        for col in year_columns:
            df[col] = (df[col] * 100).round(2)
        
        df['marketCap'] = (df['marketCap'] / 1e9).round(2)
        df['price'] = df['price'].round(2)
        
        # Calculate growth metrics
        df = pd.concat([df, self._calculate_growth_metrics(df)], axis=1)
        
        # Calculate rankings
        return self._calculate_rankings(df, weights)

    def _calculate_growth_metrics(self, df):
        roce_cols = sorted([col for col in df.columns if col.startswith('roce_')])
        op_margin_cols = sorted([col for col in df.columns if col.startswith('operating_margin_')])
        revenue_growth_cols = sorted([col for col in df.columns if col.startswith('revenue_growth_')])
        
        results = []
        
        for _, row in df.iterrows():
            roce_data = [(int(col.split('_')[-1]), val) for col, val in row[roce_cols].items() if pd.notna(val)]
            roce_years, roce_values = zip(*roce_data) if roce_data else ([], [])
            
            op_margin_data = [(int(col.split('_')[-1]), val) for col, val in row[op_margin_cols].items() if pd.notna(val)]
            op_margin_years, op_margin_values = zip(*op_margin_data) if op_margin_data else ([], [])
            
            result = {
                'roce_growth': self._calculate_regression(roce_years, roce_values) if roce_values else np.nan,
                'roce_current_year': row[roce_cols[-1]] if roce_cols else np.nan,
                'operating_margin_growth': self._calculate_regression(op_margin_years, op_margin_values) if op_margin_values else np.nan,
                'operating_margin_current_year': row[op_margin_cols[-1]] if op_margin_cols else np.nan,
                'revenue_growth_current_year': row[revenue_growth_cols[-1]] if revenue_growth_cols else np.nan
            }
            results.append(result)
        
        return pd.DataFrame(results)

    def _calculate_regression(self, years, values):
        if len(values) > 1:
            slope, _, r_value, _, _ = stats.linregress(years, values)
            return slope * (r_value ** 2)
        return np.nan

    def _calculate_rankings(self, df, weights=None):
        if weights is None:
            weights = {
                'roce_growth_rank': 0.25,
                'roce_current_year_rank': 0.20,
                'operating_margin_growth_rank': 0.25,
                'operating_margin_current_year_rank': 0.20,
                'revenue_growth_current_year_rank': 0.10
            }
        
        rankings = pd.DataFrame()
        metrics = ['roce_growth', 'operating_margin_growth', 'revenue_growth_current_year']
        
        for metric in metrics:
            rankings[f'{metric}_rank'] = df[metric].rank(ascending=False, method='min', na_option='bottom')
        
        sector_metrics = ['roce_current_year', 'operating_margin_current_year']
        for sector in df['sector'].unique():
            sector_mask = df['sector'] == sector
            sector_df = df[sector_mask]
            
            for metric in sector_metrics:
                rankings.loc[sector_mask, f'{metric}_rank'] = sector_df[metric].rank(ascending=False, method='min', na_option='bottom')
        
        rankings['final_score'] = sum(rankings[f'{metric}_rank'] * weights[f'{metric}_rank'] 
                                    for metric in metrics + sector_metrics)
        rankings['final_rank'] = rankings['final_score'].rank(method='min')
        
        return pd.concat([df, rankings], axis=1).sort_values('final_rank')