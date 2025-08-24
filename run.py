#!/usr/bin/env python3
"""
Pi-hole Statistics Display - Entry Point

This script serves as the main entry point for the Pi-hole statistics display application.
It properly imports and runs the main application from the pihole_stats package.
"""

import sys
import os

# Add src directory to Python path to import our package
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

def main():
    """Entry point that imports and runs the main application."""
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        return test_mode()
    
    try:
        from pihole_stats.main import main as app_main
        return app_main()
    except ImportError as e:
        print(f"Error importing application: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"Error running application: {e}")
        import traceback
        traceback.print_exc()
        return 1

def test_mode():
    """Test mode to validate the installation without running the full application."""
    print("🧪 Running Pi-hole Stats Display Test Mode...")
    
    # Test 1: Basic imports
    print("\n1. Testing basic imports...")
    try:
        import json
        import logging
        print("   ✓ Standard library imports successful")
    except Exception as e:
        print(f"   ✗ Standard library import failed: {e}")
        return 1
    
    # Test 2: Configuration loading
    print("\n2. Testing configuration loading...")
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"   ✓ Configuration loaded successfully")
        print(f"   ✓ Pi-hole URL: {config.get('pihole', {}).get('base_url', 'not set')}")
    except Exception as e:
        print(f"   ✗ Configuration loading failed: {e}")
        return 1
    
    # Test 3: Package imports
    print("\n3. Testing package imports...")
    try:
        from pihole_stats.config.config_manager import Config
        from pihole_stats.fonts.font_manager import FontManager
        from pihole_stats.pihole.pihole_api import PiholeAPI
        from pihole_stats.display.display_manager import DisplayManager
        from pihole_stats.utils.security import SecurityUtils
        print("   ✓ All package imports successful")
    except ImportError as e:
        print(f"   ✗ Package import failed: {e}")
        return 1
    except Exception as e:
        print(f"   ✗ Package import error: {e}")
        return 1
    
    # Test 4: Hardware dependencies
    print("\n4. Testing hardware dependencies...")
    try:
        from luma.core.interface.serial import i2c 
        from luma.core.render import canvas
        from luma.oled.device import sh1106
        print("   ✓ OLED display libraries available")
    except ImportError as e:
        print(f"   ⚠️  OLED libraries not available: {e}")
        print("   This is expected on non-Raspberry Pi systems")
    
    # Test 5: Optional dependencies
    print("\n5. Testing optional dependencies...")
    try:
        import qrcode
        print("   ✓ QR code library available")
    except ImportError as e:
        print(f"   ⚠️  QR code library not available: {e}")
    
    try:
        import requests
        print("   ✓ HTTP requests library available")
    except ImportError as e:
        print(f"   ✗ HTTP requests library not available: {e}")
        return 1
    
    # Test 6: File permissions
    print("\n6. Testing file permissions...")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_files = ['config.json', 'run.py', 'src/pihole_stats/main.py']
        for test_file in test_files:
            file_path = os.path.join(current_dir, test_file)
            if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                print(f"   ✓ {test_file} readable")
            else:
                print(f"   ✗ {test_file} not readable or missing")
                return 1
    except Exception as e:
        print(f"   ✗ File permission test failed: {e}")
        return 1
    
    print("\n🎉 All tests passed! The installation appears to be working correctly.")
    print("\nTo run the actual application, use:")
    print("   python3 run.py")
    return 0

if __name__ == "__main__":
    exit(main())
