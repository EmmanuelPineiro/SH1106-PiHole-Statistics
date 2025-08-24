import os
import logging
from pathlib import Path

class SecurityUtils:
    """Security utilities for the application"""
    
    @staticmethod
    def validate_file_permissions(filepath, required_mode=0o600):
        """Check if file has secure permissions"""
        try:
            if not os.path.exists(filepath):
                return False
            
            file_stat = os.stat(filepath)
            file_mode = file_stat.st_mode & 0o777
            
            # Check if file is readable/writable by others
            if file_mode & 0o077:  # group/other permissions
                logging.warning(f"File {filepath} has insecure permissions: {oct(file_mode)}")
                return False
            
            return True
        except Exception as e:
            logging.error(f"Permission check failed: {e}")
            return False
    
    @staticmethod
    def is_safe_path(path, base_dir="."):
        """Check if a path is safe (within base directory)"""
        try:
            base_path = Path(base_dir).resolve()
            target_path = Path(base_dir, path).resolve()
            return base_path in target_path.parents or base_path == target_path
        except Exception:
            return False
