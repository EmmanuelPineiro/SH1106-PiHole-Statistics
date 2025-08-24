#!/usr/bin/python3
import os
import sys
import signal
import logging
import time
from time import sleep

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
    log_file = config.get('files.log_file', 'stats.log')
    
    # Validate log file path
    if not SecurityUtils.is_safe_path(log_file):
        print(f"Unsafe log file path: {log_file}")
        return False
    
    try:
        logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG
        )
        
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
    # Check for required environment variables
    if not os.getenv('PIHOLE_APP_PASSWORD'):
        logging.error("PIHOLE_APP_PASSWORD not set - this is required for security")
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
