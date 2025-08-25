#!/usr/bin/python3
import os
import sys
import signal
import logging
import time
from time import sleep

# Set restrictive umask for file creation
os.umask(0o077)

# Initialize module-level logger
logger = logging.getLogger(__name__)

from luma.core.interface.serial import i2c 
from luma.core.render import canvas
from luma.oled.device import sh1106

# Import our custom classes
from .config.config_manager import Config
from .fonts.font_manager import FontManager
from .pihole.pihole_api import PiholeAPI
from .display.display_manager import DisplayManager
from .utils.security import SecurityUtils

def setup_logging(config):
    # For systemd services, log to stdout/stderr instead of file
    # This allows logs to be captured by journalctl
    try:
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s][%(name)s][%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler()  # Log to stdout for systemd
            ]
        )
        
        # Silence noisy third-party loggers
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        # Also add file logging if specified in config (optional)
        log_file = config.get('files.log_file')
        if log_file and SecurityUtils.is_safe_path(log_file):
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(logging.Formatter(
                '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logging.getLogger().addHandler(file_handler)
            
            # Set secure permissions on log file
            if os.path.exists(log_file):
                os.chmod(log_file, 0o600)
        
        return True
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        return False

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {sig}, shutting down gracefully...")
    sys.exit(0)

def validate_environment():
    """Validate the runtime environment for security"""
    # Check for required environment variables or password file
    env_password = os.getenv('PIHOLE_APP_PASSWORD')
    password_file = '/opt/pihole-stats/.app_password'
    
    if not env_password and not os.path.exists(password_file):
        logging.error("No Pi-hole password found - set PIHOLE_APP_PASSWORD environment variable or create /opt/pihole-stats/.app_password file")
        return False
    
    # If password file exists, check its permissions
    if os.path.exists(password_file):
        try:
            stat_info = os.stat(password_file)
            if stat_info.st_mode & 0o077:  # Check if readable by others
                logging.error(f"Password file {password_file} has insecure permissions (should be 600)")
                return False
        except Exception as e:
            logging.error(f"Error checking password file permissions: {e}")
            return False
    
    # Check if running as root (not recommended)
    if os.geteuid() == 0:
        logging.warning("Running as root is not recommended for security")
    
    # Check file permissions
    config_file = 'config.json'
    if os.path.exists(config_file):
        if not SecurityUtils.validate_file_permissions(config_file):
            logging.warning("config.json has insecure permissions")
    
    return True

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    try:
        config = Config()
    except FileNotFoundError:
        print("config.json not found. Please create it first.")
        return 1
    except ValueError as e:
        print(f"Invalid configuration: {e}")
        return 1
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1
    
    # Setup logging
    if not setup_logging(config):
        return 1
    
    logging.info("Starting Pi-hole Stats Display (main.py) with security enhancements")
    
    # Validate environment
    if not validate_environment():
        logging.error("Environment validation failed")
        return 1
    
    # Initialize components with error handling
    try:
        fonts = FontManager(config)
        
        # Setup display with validation
        i2c_port = config.get('display.i2c_port', 1)
        i2c_addr_str = config.get('display.i2c_address', '0x3C')
        
        # Validate I2C address
        try:
            i2c_addr = int(i2c_addr_str, 16)
            if i2c_addr < 0x08 or i2c_addr > 0x77:
                raise ValueError(f"Invalid I2C address: {i2c_addr_str}")
        except ValueError as e:
            logging.error(f"Invalid I2C address format: {e}")
            return 1
        
        serial = i2c(port=i2c_port, address=i2c_addr)
        device = sh1106(serial)
        
        display = DisplayManager(config, fonts, device)
        pihole_api = PiholeAPI(config)
        
    except Exception as e:
        logging.error(f"Failed to initialize components: {e}")
        return 1
    
    # Initialize display
    try:
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
    except Exception as e:
        logging.error(f"Failed to initialize display: {e}")
        return 1
    
    # Main loop
    while True:
        try:
            # Authenticate if needed
            if not pihole_api.session_data['sid']:
                if not pihole_api.authenticate():
                    display.show_error_screen("Auth Failed", "Retrying...")
                    sleep(10)
                    continue
            
            # Get Pi-hole data
            pihole_data = pihole_api.get_stats()
            if not pihole_data:
                display.show_error_screen("API Error", "Retrying...")
                sleep(5)
                continue
            
            # Display screens based on configuration
            screens = config.get('screens', [])
            for screen_config in screens:
                function_name = screen_config['function']
                duration_key = screen_config['duration']
                duration = config.get(f"display.{duration_key}", 5)
                
                # Get the display method
                display_method = getattr(display, function_name, None)
                if display_method:
                    # Show screen for specified duration
                    end_time = time.time() + duration
                    while time.time() < end_time:
                        if screen_config.get('requires_pihole_data', False):
                            display_method(pihole_data)
                        else:
                            display_method()
                        sleep(1)
                        
        except KeyboardInterrupt:
            logging.info("Shutting down...")
            display.show_error_screen("Shutting down...")
            sleep(2)
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            display.show_error_screen("System Error")
            sleep(5)
    
    return 0

if __name__ == "__main__":
    exit(main())
