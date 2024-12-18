import pandas as pd
import logging
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

#from finvizfinance.screener.overview import Overview
from market_data import get_market_analysis
from stock_screener import get_value_stocks, get_non_value_stocks
from utils import EmailHandler, EmailFormatter, get_price, Config, save_to_csv, setup_logging, is_monday
from utils.stock_pitch import stock_pitch
from portfolio_analyzer import analyze_portfolio_positions
from utils.stock_processing import process_positions, send_stock_analysis_email, send_portfolio_analysis_email
from stock_ranking import StockAnalyzer

def main():
    """Main execution function"""
    # Setup logging
    print('Hi, are you read to make some fucking money?!.')
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

        pitch = stock_pitch(investing_stocks, config.api['claude'])

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
            pitch, 
            investing_stocks, 
            short_stocks, 
            market_data, 
            email_handler,
            logger
        )
        
        # Only run portfolio and stock ranking analysis on Mondays
        if is_monday():
            logger.info("Running portfolio analysis (Monday schedule)")
            send_portfolio_analysis_email(config, email_handler,logger)

            #running stock ranking analysis
            logger.info("Running stock ranking analysis (Monday schedule)")
            analyzer = StockAnalyzer(config.api['financial_modeling_prep']['key'])
            ranked_df = analyzer.analyze_stocks(
                limit=config.analysis['stock_limit'],
                weights=config.analysis['weights'])
            ranked_df.to_csv(config.paths['stock_scores'], index=False)

        else:
            logger.info("Skipping portfolio and stock ranking (not Monday)")
        
        logger.info("All analyses completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise
    
    finally:
        logger.info("-------- End of Script --------")

if __name__ == "__main__":
    main()