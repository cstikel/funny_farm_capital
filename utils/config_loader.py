import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors"""
    pass

class Config:
    """
    Singleton configuration class that loads and validates settings from config.yaml
    """
    _instance = None
    _config: Dict[str, Any] = None
    _logger = logging.getLogger(__name__)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the configuration"""
        self._load_config()
        self._validate_config()
        self._setup_paths()

    def _load_config(self) -> None:
        """Load configuration from yaml file"""
        try:
            config_path = Path(__file__).parent / '../config.yaml'
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found at: {config_path}")

            with open(config_path, 'r') as file:
                self._config = yaml.safe_load(file)
                self._logger.info("Configuration loaded successfully")
        
        except yaml.YAMLError as e:
            self._logger.error(f"Error parsing config.yaml: {str(e)}")
            raise ConfigValidationError(f"Invalid YAML format: {str(e)}")
        
        except Exception as e:
            self._logger.error(f"Error loading configuration: {str(e)}")
            raise

    def _validate_config(self) -> None:
        """Validate the configuration structure and required fields"""
        required_sections = ['email', 'stock_filters', 'api', 'paths', 'portfolio']
        
        # Check for required top-level sections
        for section in required_sections:
            if section not in self._config:
                raise ConfigValidationError(f"Missing required configuration section: {section}")

        # Validate email configuration
        self._validate_email_config()
        
        # Validate stock filters
        self._validate_stock_filters()
        
        # Validate API configuration
        self._validate_api_config()
        
        # Validate paths
        self._validate_paths_config()
        
        # Validate portfolio configuration
        self._validate_portfolio_config()

    def _validate_portfolio_config(self) -> None:
        """Validate portfolio configuration section"""
        portfolio_config = self._config.get('portfolio', {})
        
        if 'exclude_stocks' not in portfolio_config:
            raise ConfigValidationError("Missing exclude_stocks in portfolio configuration")
        
        if not isinstance(portfolio_config['exclude_stocks'], list):
            raise ConfigValidationError("exclude_stocks must be a list")
        
        if 'negative_weight' in portfolio_config and not isinstance(portfolio_config['negative_weight'], (int, float)):
            raise ConfigValidationError("negative_weight must be a number")

    def _validate_email_config(self) -> None:
        """Validate email configuration section"""
        required_email_fields = ['recipients', 'sender', 'password', 'smtp']
        email_config = self._config.get('email', {})
        
        for field in required_email_fields:
            if field not in email_config:
                raise ConfigValidationError(f"Missing required email configuration field: {field}")
        
        if not isinstance(email_config['recipients'], list):
            raise ConfigValidationError("Email recipients must be a list")
        
        smtp_config = email_config.get('smtp', {})
        if 'server' not in smtp_config or 'port' not in smtp_config:
            raise ConfigValidationError("SMTP configuration must include server and port")

    def _validate_stock_filters(self) -> None:
        """Validate stock filters configuration section"""
        required_filter_types = ['long', 'short']
        filters = self._config.get('stock_filters', {})
        
        for filter_type in required_filter_types:
            if filter_type not in filters:
                raise ConfigValidationError(f"Missing required filter type: {filter_type}")
            
            if not isinstance(filters[filter_type], dict):
                raise ConfigValidationError(f"Stock filters for {filter_type} must be a dictionary")
            
            if 'rank_condition' not in filters[filter_type]:
                raise ConfigValidationError(f"Missing rank_condition in {filter_type} filters")
            
            if not isinstance(filters[filter_type]['rank_condition'], (int, float)):
                raise ConfigValidationError(f"rank_condition in {filter_type} filters must be a number")

    def _validate_api_config(self) -> None:
        """Validate API configuration section"""
        api_config = self._config.get('api', {})
        
        if 'financial_modeling_prep' not in api_config:
            raise ConfigValidationError("Missing Financial Modeling Prep API configuration")
        
        if 'key' not in api_config['financial_modeling_prep']:
            raise ConfigValidationError("Missing API key for Financial Modeling Prep")

    def _validate_paths_config(self) -> None:
        """Validate paths configuration section"""
        required_paths = ['stock_scores', 'investing_stocks', 'short_stocks', 'portfolio_file']
        paths_config = self._config.get('paths', {})
        
        for path in required_paths:
            if path not in paths_config:
                raise ConfigValidationError(f"Missing required path configuration: {path}")

    def _setup_paths(self) -> None:
        """Convert path strings to Path objects and ensure directories exist"""
        for key, path_str in self._config['paths'].items():
            path = Path(path_str)
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            # Update config with Path object
            self._config['paths'][key] = path

    def __getattr__(self, name: str) -> Any:
        """Handle attribute access for config sections"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key"""
        return self._config.get(key, default)

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Get a nested configuration value"""
        current = self._config
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current

    @classmethod
    def reload(cls) -> None:
        """Force reload of the configuration"""
        cls._instance = None
        cls._config = None
        return cls()

    def __str__(self) -> str:
        """String representation of the configuration"""
        return f"Configuration(sections={list(self._config.keys())})"

    def __repr__(self) -> str:
        """Detailed string representation of the configuration"""
        return f"Configuration(loaded_from={Path(__file__).parent / 'config.yaml'})"