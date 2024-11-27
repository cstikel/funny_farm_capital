from typing import Dict, List, Optional
import logging
import pandas as pd
from datetime import datetime
from finvizfinance.screener.overview import Overview
from stock_screener import get_value_stocks, get_non_value_stocks
from portfolio_analyzer import analyze_portfolio_positions
from utils.general import save_to_csv
from utils import EmailFormatter, get_price
import yfinance as yf
from datetime import datetime, timedelta

# Then your classes and functions follow...

class OHLCVFetcher:
    """
    A class to fetch and process OHLCV (Open, High, Low, Close, Volume) data for stocks
    """
    
    def __init__(self, ticker: str):
        """
        Initialize with stock ticker symbol
        
        Parameters:
        ticker (str): Stock ticker symbol (e.g., 'AAPL' for Apple)
        """
        self.ticker = ticker
        self.data = None
        
    def fetch_data(self, 
                   period: str = "6mo",
                   interval: str = "1d") -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance
        
        Parameters:
        period (str): Time period to fetch. Options: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', etc.
        interval (str): Data interval. Options: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
        
        Returns:
        pd.DataFrame: DataFrame with OHLCV data
        """
        try:
            # Create ticker object
            stock = yf.Ticker(self.ticker)
            
            # Fetch historical data
            self.data = stock.history(period=period, interval=interval)
            
            # Reset index to make date a column
            self.data = self.data.reset_index()
            
            # Rename columns to standard format
            self.data.columns = [col.lower() for col in self.data.columns]
            
            # Calculate additional metrics
            self.data['typical_price'] = (self.data['high'] + self.data['low'] + self.data['close']) / 3
            self.data['daily_range'] = self.data['high'] - self.data['low']
            self.data['daily_return'] = self.data['close'].pct_change()
            
            return self.data
            
        except Exception as e:
            print(f"Error fetching data for {self.ticker}: {str(e)}")
            return pd.DataFrame()
    
    def get_latest_data(self) -> dict:
        """
        Get the most recent OHLCV data point
        
        Returns:
        dict: Dictionary containing latest OHLCV data
        """
        if self.data is None or len(self.data) == 0:
            return {}
            
        latest = self.data.iloc[-1]
        return {
            'date': latest['date'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume'],
            'typical_price': latest['typical_price'],
            'daily_range': latest['daily_range'],
            'daily_return': latest['daily_return']
        }
    
    def get_summary_stats(self) -> dict:
        """
        Calculate summary statistics for the OHLCV data
        
        Returns:
        dict: Dictionary containing summary statistics
        """
        if self.data is None or len(self.data) == 0:
            return {}
            
        return {
            'avg_daily_volume': self.data['volume'].mean(),
            'avg_daily_range': self.data['daily_range'].mean(),
            'avg_daily_return': self.data['daily_return'].mean(),
            'return_volatility': self.data['daily_return'].std(),
            'highest_price': self.data['high'].max(),
            'lowest_price': self.data['low'].min(),
            'price_range': self.data['high'].max() - self.data['low'].min(),
            'days_of_data': len(self.data)
        }


class EarlyTrendDetector:
    def __init__(self, price_data: pd.DataFrame, config: dict):
        """
        Initialize with price data and configuration parameters
        
        Parameters:
        price_data (pd.DataFrame): DataFrame containing OHLCV data
        config (dict): Configuration dictionary containing trend detection parameters
        """
        self.df = price_data
        self.config = config['trend_detection']
        self.signals = pd.DataFrame(index=self.df.index)
        
    def identify_early_trend(self, lookback_period: Optional[int] = None) -> Dict[str, float]:
        """
        Identify early trend signals using configuration parameters
        """
        lookback = lookback_period or self.config['lookback_period']
        weights = self.config['indicator_weights']
        thresholds = self.config['thresholds']
        
        signals = {}
        
        # 1. Price-MA Relationships
        ma_score = 0
        if (self.df['close'].iloc[-1] > self.df['sma_10'].iloc[-1] and 
            self.df['sma_10'].iloc[-1] > self.df['sma_20'].iloc[-1]):
            ma_score = weights['price_ma']
            
        # 2. Volume Confirmation
        vol_score = 0
        recent_volume_ratio = self.df['volume_ratio'].iloc[-lookback:]
        if (recent_volume_ratio > thresholds['volume_ratio']).any():
            vol_score = weights['volume']
            
        # 3. Momentum Indicators
        momentum_score = 0
        if (self.df['rsi'].iloc[-1] > thresholds['rsi_lower'] and 
            self.df['rsi'].iloc[-1] < thresholds['rsi_upper'] and 
            self.df['roc_5'].iloc[-1] > 0):
            momentum_score = weights['momentum']
            
        # 4. MACD Signal
        macd_score = 0
        if (self.df['macd'].iloc[-1] > self.df['macd_signal'].iloc[-1] and
            self.df['macd'].iloc[-2] <= self.df['macd_signal'].iloc[-2]):
            macd_score = weights['macd']
            
        # 5. Bollinger Band Position
        bb_score = 0
        if (self.df['close'].iloc[-1] > self.df['bb_middle'].iloc[-1] and
            self.df['close'].iloc[-1] < self.df['bb_upper'].iloc[-1]):
            bb_score = weights['bollinger']
            
        total_score = ma_score + vol_score + momentum_score + macd_score + bb_score
        
        return {
            'total_score': total_score,
            'ma_score': ma_score,
            'volume_score': vol_score,
            'momentum_score': momentum_score,
            'macd_score': macd_score,
            'bb_score': bb_score
        }
    
    def get_trend_signals(self, min_score: Optional[float] = None) -> Dict:
        """Get trend signals with detailed analysis"""
        self.calculate_indicators()
        signals = self.identify_early_trend()
        
        min_score = min_score or self.config['min_score']
        
        if signals['total_score'] >= min_score:
            return {
                'trend_strength': signals['total_score'],
                'signal_type': 'strong_uptrend' if signals['total_score'] > 0.8 else 'potential_uptrend',
                'confidence': signals['total_score'] * 100,
                'contributing_factors': {
                    key: value for key, value in signals.items() if value > 0
                }
            }
        return None



def process_positions(stock_scores, filters, output_file, position_type):
    """Generic function to process both long and short positions with trend detection"""
    logger = logging.getLogger(__name__)
    logger.info(f"Processing {position_type} positions...")
    
    try:
        # Get appropriate scores based on position type
        if position_type == "long":
            scores = get_value_stocks(stock_scores)
        else:
            scores = get_non_value_stocks(stock_scores)
        
        # Extract screening filters (excluding rank_condition)
        screening_filters = {k: v for k, v in filters.items() if k != 'rank_condition'}
        
        # Apply initial filters
        foverview = Overview()
        foverview.set_filter(filters_dict=screening_filters)
        df_overview = foverview.screener_view()
        trending_stocks = df_overview['Ticker'].to_list()
        
        # Filter and sort stocks
        final_stocks = scores[scores['ticker'].isin(trending_stocks)].sort_values(by='final_rank')
        
        # Apply rank condition
        rank_condition = filters['rank_condition']
        if position_type == "long":
            filtered_stocks = final_stocks[final_stocks['final_rank'] <= rank_condition]
        else:
            filtered_stocks = final_stocks[final_stocks['final_rank'] >= rank_condition]
        
        # Apply trend detection to filtered stocks
        trend_filtered_stocks = []
        for ticker in filtered_stocks['ticker']:
            try:
                fetcher = OHLCVFetcher(ticker)
                price_data = fetcher.fetch_data(
                    period=filters['trend_detection']['thresholds']['price_data_period']
                )
                
                if not price_data.empty:
                    trend_detector = EarlyTrendDetector(price_data, filters)
                    signals = trend_detector.get_trend_signals()
                    
                    # For long positions, look for uptrends
                    # For short positions, look for downtrends (you might want to modify EarlyTrendDetector for this)
                    if position_type == "long" and signals:
                        trend_filtered_stocks.append(ticker)
                    elif position_type == "short" and not signals:
                        trend_filtered_stocks.append(ticker)
                        
            except Exception as e:
                logger.warning(f"Error analyzing trends for {ticker}: {str(e)}")
                continue
        
        # Filter final stocks to only those that passed trend detection
        filtered_stocks = filtered_stocks[filtered_stocks['ticker'].isin(trend_filtered_stocks)]
        
        # Add additional data
        filtered_stocks['price_picked'] = filtered_stocks['ticker'].apply(get_price)
        filtered_stocks['date'] = datetime.today().strftime('%Y_%m_%d')
        
        # Add trend analysis data
        trend_data = []
        for ticker in filtered_stocks['ticker']:
            fetcher = OHLCVFetcher(ticker)
            price_data = fetcher.fetch_data(period=filters['trend_detection']['thresholds']['price_data_period'])
            trend_detector = EarlyTrendDetector(price_data)
            signals = trend_detector.get_trend_signals()
            if signals:
                trend_data.append({
                    'ticker': ticker,
                    'trend_strength': signals['trend_strength'],
                    'signal_type': signals['signal_type'],
                    'confidence': signals['confidence']
                })
        
        # Merge trend data with filtered stocks
        trend_df = pd.DataFrame(trend_data)
        if not trend_df.empty:
            filtered_stocks = filtered_stocks.merge(trend_df, on='ticker', how='left')
        
        # Save results
        save_to_csv(filtered_stocks, output_file)
        
        logger.info(f"Found {len(filtered_stocks)} {position_type} positions with trend confirmation")
        return filtered_stocks
        
    except Exception as e:
        logger.error(f"Error processing {position_type} positions: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error
    


def send_stock_analysis_email(config, investing_stocks, short_stocks, market_data, email_handler, logger):
    """Send stock analysis email"""
    try:
        logger.info("Preparing stock analysis email...")
        email_body = EmailFormatter.format_stock_analysis(
            investing_stocks, 
            short_stocks, 
            market_data
        )
        
        email_handler.send_email(
            to_emails=config.email['recipients'],
            email_body=email_body,
            subject=f"{datetime.today().strftime('%Y-%m-%d')} Stock Analysis"
        )
        logger.info("Stock analysis email sent successfully")
    except Exception as e:
        logger.error(f"Error sending stock analysis email: {str(e)}")
        raise

def send_portfolio_analysis_email(config, email_handler, logger):
    """Send portfolio rebalance analysis email"""
    try:
        logger.info("Running portfolio analysis...")
        
        # Get portfolio settings from config
        portfolio_settings = config.portfolio
        
        portfolio_changes, sharpe_improvement, total_value, current_portfolio = analyze_portfolio_positions(
            portfolio_file=config.paths['portfolio_file'],
            exclude_stocks=portfolio_settings['exclude_stocks'],
            negative_weight=portfolio_settings.get('negative_weight', 10)
        )
        
        logger.info("Preparing portfolio analysis email...")
        email_body = EmailFormatter.format_portfolio_rebalance(
            portfolio_changes,
            sharpe_improvement,
            total_value,
            portfolio_settings['exclude_stocks'],
            current_portfolio
        )
        
        email_handler.send_email(
            to_emails=config.email['recipients'],
            email_body=email_body,
            subject=f"{datetime.today().strftime('%Y-%m-%d')} Portfolio Rebalance"
        )
        logger.info("Portfolio analysis email sent successfully")
    except Exception as e:
        logger.error(f"Error sending portfolio analysis email: {str(e)}")
        raise