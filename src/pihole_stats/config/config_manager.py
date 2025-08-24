import json
import os
import logging

class Config:
    """Configuration manager with security validation"""
    def __init__(self, config_file='config.json'):
        # Validate config file path to prevent path traversal
        if not self._is_safe_path(config_file):
            raise ValueError(f"Unsafe config file path: {config_file}")
        
        # Check file permissions
        if os.path.exists(config_file):
            file_stat = os.stat(config_file)
            if file_stat.st_mode & 0o044:  # Check if readable by group/others
                logging.warning(f"Config file {config_file} is readable by others. Consider chmod 600")
        
        with open(config_file, 'r') as f:
            self.data = json.load(f)
        
        # Validate configuration after loading
        self._validate_config()
    
    def get(self, path, default=None):
        """Get nested config value using dot notation (e.g., 'display.width')"""
        # Validate path to prevent injection
        if not isinstance(path, str) or '..' in path or path.startswith('/'):
            logging.warning(f"Invalid config path: {path}")
            return default
            
        keys = path.split('.')
        value = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def _is_safe_path(self, path):
        """Check if path is safe (no directory traversal)"""
        if not isinstance(path, str):
            return False
        return not ('..' in path or path.startswith('/') or path.startswith('~'))
    
    def _validate_config(self):
        """Validate configuration values for security"""
        # Validate URLs
        base_url = self.get('pihole.base_url', '')
        if base_url and not self._is_valid_url(base_url):
            raise ValueError(f"Invalid base_url: {base_url}")
        
        # Validate timeout
        timeout = self.get('pihole.timeout', 10)
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
            raise ValueError(f"Invalid timeout value: {timeout}")
        
        # Validate display settings
        width = self.get('display.width', 128)
        height = self.get('display.height', 64)
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            raise ValueError("Invalid display dimensions")
    
    def _is_valid_url(self, url):
        """Basic URL validation"""
        import re
        pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(pattern.match(url))
