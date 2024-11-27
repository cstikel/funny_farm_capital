import pandas as pd
import logging
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

#from finvizfinance.screener.overview import Overview
from market_data import get_market_analysis
from stock_screener import get_value_stocks, get_non_value_stocks
from utils import EmailHandler, EmailFormatter, get_price, Config, save_to_csv, setup_logging, is_monday
from portfolio_analyzer import analyze_portfolio_positions
from utils.stock_processing import process_positions, send_stock_analysis_email, send_portfolio_analysis_email


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