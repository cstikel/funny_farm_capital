import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

from finvizfinance.screener.overview import Overview
from market_data import get_market_analysis
from stock_screener import get_value_stocks, get_non_value_stocks
from utils import EmailHandler, EmailFormatter, get_price, Config, save_to_csv, setup_logging
from portfolio_analyzer import analyze_portfolio_positions

def process_positions(stock_scores, filters, output_file, position_type):
    """Generic function to process both long and short positions"""
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
        
        # Apply filters
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
        
        # Add additional data
        filtered_stocks['price_picked'] = filtered_stocks['ticker'].apply(get_price)
        filtered_stocks['date'] = datetime.today().strftime('%Y_%m_%d')
        
        # Save results
        save_to_csv(filtered_stocks, output_file)
        
        logger.info(f"Found {len(filtered_stocks)} {position_type} positions")
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

def is_monday():
    """Check if today is Monday"""
    return datetime.today().weekday() == 0

def main():
    """Main execution function"""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting analysis scripts...")
    
    try:
        # Load configuration
        config = Config()
        logger.info("Configuration loaded successfully")
        
        # Initialize email handler
        email_handler = EmailHandler('config.yaml')
        logger.info("Email handler initialized")
        
        # Process stock analysis
        logger.info("Starting stock analysis...")
        stock_scores = pd.read_csv(config.paths['stock_scores'])
        logger.info(f"Loaded {len(stock_scores)} stock scores")
        
        investing_stocks = process_positions(
            stock_scores=stock_scores,
            filters=config.stock_filters['long'],
            output_file=config.paths['investing_stocks'],
            position_type="long"
        )
        
        short_stocks = process_positions(
            stock_scores=stock_scores,
            filters=config.stock_filters['short'],
            output_file=config.paths['short_stocks'],
            position_type="short"
        )
        
        market_data = get_market_analysis()
        
        # Send stock analysis email
        send_stock_analysis_email(
            config, 
            investing_stocks, 
            short_stocks, 
            market_data, 
            email_handler,
            logger
        )
        
        # Only run portfolio analysis on Mondays
        if is_monday():
            logger.info("Running portfolio analysis (Monday schedule)")
            send_portfolio_analysis_email(
                config,
                email_handler,
                logger
            )
        else:
            logger.info("Skipping portfolio analysis (not Monday)")
        
        logger.info("All analyses completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise
    
    finally:
        logger.info("-------- End of Script --------")

if __name__ == "__main__":
    main()