import logging
import pandas as pd
from datetime import datetime  

def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stock_analysis.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def save_to_csv(df, filepath, mode='a', header=False):
    """Save DataFrame to CSV with error handling"""
    try:
        if mode == 'a':
            with open(filepath, 'a') as f:
                f.write('\n')
        df.to_csv(filepath, mode=mode, header=header, index=False)
        logging.info(f"Successfully saved data to {filepath}")
    except Exception as e:
        logging.error(f"Error saving to {filepath}: {str(e)}")
        raise

def is_monday():
    """Check if today is Monday"""
    return datetime.today().weekday() == 5