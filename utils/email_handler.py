import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime
import yaml
import pandas as pd

class EmailHandler:
    def __init__(self, config_file='config.yml'):
        """Initialize email handler with configuration"""
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file):
        """Load configuration from YAML file"""
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)
    
    def send_email(self, to_emails, email_body, subject=None):
        """Send email to recipients"""
        if isinstance(to_emails, str):
            to_emails = [to_emails]
            
        msg = MIMEMultipart()
        msg["From"] = self.config['email']['sender']
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject or f"{date.today().strftime('%Y-%m-%d')} Auto-Generated Report"
        
        email_text = f"""
<pre style="font-family: Courier New, Courier, monospace;">
{email_body}
</pre>
"""
        msg.attach(MIMEText(email_text, "html"))
        
        try:
            server = smtplib.SMTP(
                self.config['email']['smtp']['server'],
                self.config['email']['smtp']['port']
            )
            server.starttls()
            server.login(
                self.config['email']['sender'],
                self.config['email']['password']
            )
            server.sendmail(self.config['email']['sender'], to_emails, msg.as_string())
            print(f"Email sent successfully to {len(to_emails)} recipients!")
        except Exception as e:
            print(f"Failed to send email: {e}")
        finally:
            server.quit()

class EmailFormatter:
    @staticmethod
    def format_stock_analysis(investing_stocks, short_stocks, market_data):
        """Format stock analysis email with trend scores"""
        def format_dataframe(df):
            display_columns = ['symbol', 'final_rank']
            if 'trend_strength' in df.columns:
                display_columns.append('trend_strength')
                
            df_display = df[display_columns].copy()
            df_display = df_display.round(2)
            
            # Rename columns for display
            column_mapping = {
                'symbol': 'SYM',
                'final_rank': 'RANK',
                'trend_strength': 'TREND'
            }
            df_display.columns = [column_mapping.get(col, col) for col in df_display.columns]
            
            # Format numeric columns
            for col in df_display.columns:
                if col == 'TREND':
                    df_display[col] = df_display[col].map('{:.2f}'.format)
                elif col != 'SYM':
                    df_display[col] = df_display[col].map('{:.0f}'.format)
            
            # Set column spacing
            col_space = {
                'SYM': 6,
                'RANK': 6,
                'TREND': 6
            }
            
            return df_display.to_string(
                index=False,
                justify='left',
                col_space=col_space
            )

        email_body = []
        
        email_body.append(f"Stock Analysis - {datetime.today().strftime('%b %d, %Y')}")
        email_body.append("=" * 35)
        email_body.append("")
        
        # Market Analysis
        email_body.append("MARKET ANALYSIS")
        email_body.append("-" * 15)
        email_body.extend(market_data)
        email_body.append("")
        
        # Long Positions
        email_body.append("LONG POSITIONS")
        email_body.append("-" * 15)
        if len(investing_stocks) > 0:
            email_body.append(format_dataframe(investing_stocks))
            email_body.append("")
            email_body.append(f"Total: {len(investing_stocks)}")
            email_body.append(f"Avg Rank: {investing_stocks['final_rank'].mean():.0f}")
            if 'trend_strength' in investing_stocks.columns:
                email_body.append(f"Avg Trend Score: {investing_stocks['trend_strength'].mean():.2f}")
        else:
            email_body.append("No long positions identified today.")
        email_body.append("")
        
        # Short Positions
        email_body.append("SHORT POSITIONS")
        email_body.append("-" * 15)
        if len(short_stocks) > 0:
            email_body.append(format_dataframe(short_stocks))
            email_body.append("")
            email_body.append(f"Total: {len(short_stocks)}")
            email_body.append(f"Avg Rank: {short_stocks['final_rank'].mean():.0f}")
            if 'trend_strength' in short_stocks.columns:
                email_body.append(f"Avg Trend Score: {short_stocks['trend_strength'].mean():.2f}")
        else:
            email_body.append("No short positions identified today.")
        
        email_body.append("\n" + "-" * 35)
        email_body.append("Auto-generated report - Do not reply")
        
        return "\n".join(email_body)
    

    @staticmethod
    def format_portfolio_rebalance(portfolio_changes, sharpe_improvement, total_value, excluded_stocks, current_portfolio):
        email_body = []
        
        # Header
        email_body.append(f"PORTFOLIO REBALANCE")
        email_body.append(f"{datetime.today().strftime('%b %d, %Y')}")
        email_body.append("=" * 30)
        
        # Overview - One stat per line for better mobile readability
        email_body.append("\nPORTFOLIO VALUE")
        email_body.append(f"${total_value:,.0f}")
        
        email_body.append("\nSHARPE IMPROVEMENT")
        email_body.append(f"{sharpe_improvement:.1f}%")
        
        # Excluded stocks
        if excluded_stocks:
            excluded_df = current_portfolio[current_portfolio['Symbol'].isin(excluded_stocks)]
            excluded_value = excluded_df['Mkt Val (Market Value)'].sum()
            email_body.append("\nEXCLUDED")
            email_body.append(f"${excluded_value:,.0f}")
            email_body.append(f"{', '.join(excluded_stocks)}")
        
        # Trades - Format each trade on separate lines
        email_body.append("\nTRADES")
        email_body.append("-" * 30)
        
        for _, row in portfolio_changes.iterrows():
            email_body.append(f"{row['Symbol']:<6}")
            email_body.append(f"Current: {row['current_percent']:>3.0f}%")
            email_body.append(f"Target:  {row['ideal_percent']:>3.0f}%")
            email_body.append(f"Change:  ${row['cash_change']:,.0f}")
            email_body.append("-" * 30)
        
        email_body.append("\nAuto-generated report")
        
        return "\n".join(email_body)