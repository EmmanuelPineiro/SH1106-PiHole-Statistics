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
    try:
        from pihole_stats.main import main as app_main
        return app_main()
    except ImportError as e:
        print(f"Error importing application: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"Error running application: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
