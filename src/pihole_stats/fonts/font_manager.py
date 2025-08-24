import os
import logging
from PIL import ImageFont

class FontManager:
    """Manage fonts with fallback"""
    def __init__(self, config):
        self.config = config
        self.fonts = {}
        self._load_fonts()
    
    def _load_fonts(self):
        mono_path = self.config.get('fonts.mono_font_path')
        display_path = self.config.get('fonts.display_font_path')
        sizes = self.config.get('fonts.sizes', {})
        
        for name, size in sizes.items():
            font_path = display_path if name == 'logo' else mono_path
            self.fonts[name] = self._load_font_safe(font_path, size)
    
    def _load_font_safe(self, font_path, size):
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except (OSError, IOError) as e:
            logging.warning(f"Could not load font {font_path}: {e}")
        return ImageFont.load_default()
    
    def get(self, name):
        return self.fonts.get(name, ImageFont.load_default())
