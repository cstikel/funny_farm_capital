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
    def format_portfolio_rebalance(portfolio_changes, sharpe_improvement, total_value, exclude_stocks, current_portfolio):
        """Format portfolio rebalance email"""
        email_body = []
        
        email_body.append("Portfolio Rebalance Analysis")
        email_body.append("=" * 40)
        email_body.append(f"Date: {date.today().strftime('%Y-%m-%d')}")
        email_body.append(f"Value: ${total_value:,.0f}")
        
        # Excluded positions
        email_body.append("\nExcluded Positions:")
        email_body.append("-" * 40)
        excluded_df = current_portfolio[current_portfolio['Symbol'].isin(exclude_stocks)].copy()
        excluded_df['pct'] = (excluded_df['Mkt Val (Market Value)'] / total_value * 100).round(0)
        for _, row in excluded_df.iterrows():
            email_body.append(f"{row['Symbol']:<6} {int(row['pct'])}%")
        
        email_body.append(f"\nSharpe Improvement: {sharpe_improvement:.1f}%")
        
        # Required changes
        email_body.append("\nRequired Changes:")
        email_body.append("-" * 40)
        email_body.append(f"{'Stock':<6} {'Cur->Tgt':>11} {'Change':>12}")
        email_body.append("-" * 40)
        
        for _, row in portfolio_changes.iterrows():
            percentages = f"{int(row['current_percent'])} -> {int(row['ideal_percent'])}%"
            cash_change = f"{int(row['cash_change']):,}"
            email_body.append(
                f"{row['Symbol']:<6} "
                f"{percentages:>11} "
                f"{cash_change:>12}"
            )
        
        email_body.append("-" * 40)
        email_body.append(f"{'Total':<6} {'':>11} {portfolio_changes['cash_change'].sum():>12,}")
        
        return "\n".join(email_body)
    
    @staticmethod
    def format_stock_analysis(investing_stocks, short_stocks, market_data):
        """Format stock analysis email"""
        def format_dataframe(df):
            df_display = df[['ticker', 'roce_rank', 'coef_rank', 'final_rank']].copy()
            df_display = df_display.round(0)
            df_display.columns = ['TKR', 'ROCE', 'COEF', 'RANK']
            
            numeric_cols = df_display.select_dtypes(include=['float64']).columns
            for col in numeric_cols:
                df_display[col] = df_display[col].map('{:.0f}'.format)
            
            return df_display.to_string(
                index=False,
                justify='left',
                col_space={'TKR': 6, 'ROCE': 6, 'COEF': 6, 'RANK': 6}
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
        else:
            email_body.append("No short positions identified today.")
        
        email_body.append("\n" + "-" * 35)
        email_body.append("Auto-generated report - Do not reply")
        
        return "\n".join(email_body)