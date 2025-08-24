import logging
import html
import re
from luma.core.render import canvas
from PIL import Image
from ..utils.system_info import SystemInfo

class DisplayManager:
    """Manage display screens with security enhancements"""
    def __init__(self, config, fonts, device):
        self.config = config
        self.fonts = fonts
        self.device = device
        self.width = config.get('display.width', 128)
        self.height = config.get('display.height', 64)
        self.x = 0
        self.top = 0
        self.system_info = SystemInfo()
        
        # Validate display dimensions
        if not isinstance(self.width, int) or not isinstance(self.height, int):
            raise ValueError("Display dimensions must be integers")
        if self.width <= 0 or self.height <= 0 or self.width > 1024 or self.height > 1024:
            raise ValueError("Invalid display dimensions")
    
    def _sanitize_text(self, text, max_length=50):
        """Sanitize text input for display"""
        if not isinstance(text, (str, int, float)):
            return "Invalid"
        
        text = str(text)
        # Remove any potential control characters
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
        # Limit length to prevent buffer overflow
        text = text[:max_length]
        # Escape HTML entities (though not strictly needed for OLED)
        text = html.escape(text)
        return text
    
    def _validate_pihole_data(self, pihole_data):
        """Validate Pi-hole data before display"""
        if not isinstance(pihole_data, dict):
            return False
        
        # Check for new API structure
        if 'queries' not in pihole_data:
            return False
        
        queries = pihole_data.get('queries', {})
        required_query_fields = ['percent_blocked', 'blocked']
        for field in required_query_fields:
            if field not in queries:
                return False
        
        return True
    
    def show_error_screen(self, message, submessage=None):
        message = self._sanitize_text(message, 20)
        if submessage:
            submessage = self._sanitize_text(submessage, 20)
        
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            draw.text((self.x, self.top), message, font=self.fonts.get('medium'), fill="white")
            if submessage:
                draw.text((self.x, self.top+16), submessage, font=self.fonts.get('medium'), fill="white")
    
    def show_ads_blocked_screen(self, pihole_data):
        if not self._validate_pihole_data(pihole_data):
            self.show_error_screen("Invalid Data")
            return
        
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            
            ads_percentage = self._sanitize_text(pihole_data.get("queries", {}).get("percent_blocked", "0"), 10)
            ads_blocked = self._sanitize_text(pihole_data.get("queries", {}).get("blocked", "0"), 15)
            
            draw.text((self.x, self.top-2), f"{ads_percentage}%", font=self.fonts.get('large'), fill="white")
            draw.text((self.x, self.top+34), "ADs BLOCKED:", font=self.fonts.get('normal'), fill="white")
            draw.text((self.x, self.top+48), str(ads_blocked), font=self.fonts.get('normal'), fill="white")
    
    def show_network_stats_screen(self, pihole_data):
        IP = self.system_info.get_ip_address()
        
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            
            ads_percentage = pihole_data.get("queries", {}).get("percent_blocked", "0")
            ads_blocked = pihole_data.get("queries", {}).get("blocked", "0")
            dns_queries = pihole_data.get("queries", {}).get("total", "0")
            
            draw.text((self.x, self.top), IP, font=self.fonts.get('normal'), fill="white")
            draw.text((self.x, self.top+20), f"BLK: {ads_percentage}%", font=self.fonts.get('medium'), fill="white")
            draw.text((self.x, self.top+34), f"ADS: {ads_blocked}", font=self.fonts.get('medium'), fill="white")
            draw.text((self.x, self.top+48), f"QRY: {dns_queries}", font=self.fonts.get('medium'), fill="white")
    
    def show_hardware_screen(self, pihole_data=None):
        hardware_info = self.system_info.get_hardware_info()
        
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            
            if hardware_info:
                cpu_percentage = round(float(hardware_info['cpu_load']) * 10, 2)
                draw.text((self.x, self.top), f"CPU: {cpu_percentage}%", font=self.fonts.get('medium'), fill="white")
                draw.text((self.x, self.top+16), f"RAM: {hardware_info['memory']}", font=self.fonts.get('medium'), fill="white")
                draw.text((self.x, self.top+32), f"USG: {hardware_info['disk']}", font=self.fonts.get('medium'), fill="white")
                draw.text((self.x, self.top+48), f"TEMP: {hardware_info['temperature']}°C", font=self.fonts.get('medium'), fill="white")
            else:
                draw.text((self.x, self.top), "Hardware Error", font=self.fonts.get('medium'), fill="white")
    
    def show_qr_code_screen(self, pihole_data=None):
        """Display QR code for configured URL (typically Pi-hole login)"""
        try:
            # Get QR code configuration
            qr_enabled = self.config.get('qr_code.enabled', True)
            if not qr_enabled:
                self._show_fallback_logo_with_text("QR Disabled")
                return
            
            # Get URL from config with fallback to Pi-hole admin URL
            qr_url = self.config.get('qr_code.url')
            if not qr_url:
                # Fallback: derive from Pi-hole base URL
                pihole_url = self.config.get('pihole.base_url', 'http://localhost')
                
                # Remove /admin/api suffix if present and add /admin for login
                if pihole_url.endswith('/admin/api'):
                    qr_url = pihole_url[:-10] + '/admin'  # Remove '/admin/api', add '/admin'
                elif pihole_url.endswith('/admin/api/'):
                    qr_url = pihole_url[:-11] + '/admin'  # Remove '/admin/api/', add '/admin'
                else:
                    qr_url = pihole_url.rstrip('/') + '/admin'
            
            # Get QR code display settings
            qr_box_size = self.config.get('qr_code.box_size', 2)
            qr_border = self.config.get('qr_code.border', 2)
            qr_error_correction = self.config.get('qr_code.error_correction', 'M')
            
            # Map error correction setting
            error_correction_map = {
                'L': 'ERROR_CORRECT_L',    # ~7% correction
                'M': 'ERROR_CORRECT_M',    # ~15% correction
                'Q': 'ERROR_CORRECT_Q',    # ~25% correction
                'H': 'ERROR_CORRECT_H'     # ~30% correction
            }
            error_correction = getattr(
                __import__('qrcode.constants', fromlist=[error_correction_map.get(qr_error_correction, 'ERROR_CORRECT_M')]),
                error_correction_map.get(qr_error_correction, 'ERROR_CORRECT_M')
            )
            
            # Generate QR code
            import qrcode
            qr = qrcode.QRCode(
                version=1,  # Small QR code (21x21 modules)
                error_correction=error_correction,
                box_size=qr_box_size,
                border=qr_border,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Convert to PIL image
            qr_image = qr.make_image(fill_color="white", back_color="black")
            
            # Convert to 1-bit for OLED display
            qr_image = qr_image.convert('1')
            
            # Center the QR code on screen
            qr_width, qr_height = qr_image.size
            x_offset = (self.width - qr_width) // 2
            y_offset = (self.height - qr_height) // 2
            
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="black", fill="black")
                draw.bitmap((x_offset, y_offset), qr_image, fill="white")
                
        except ImportError:
            # Fallback if qrcode library is not available
            self._show_fallback_logo_with_text("QR lib missing")
        except Exception as e:
            logging.error(f"QR code generation error: {e}")
            self._show_fallback_logo_with_text("QR Error")
    
    def _is_safe_image_path(self, path):
        """Validate image file path for security"""
        if not isinstance(path, str):
            return False
        
        # Prevent directory traversal
        if '..' in path or path.startswith('/') or path.startswith('~'):
            return False
        
        # Only allow certain file extensions
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            return False
        
        return True
    
    def _show_fallback_logo_with_text(self, message="Pi-hole"):
        """Show fallback text when QR code generation fails"""
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            # Center the text
            text_width = len(message) * 6  # Approximate character width
            x_pos = (self.width - text_width) // 2
            draw.text((x_pos, self.top + 20), message, font=self.fonts.get('medium'), fill="white")
            draw.text((self.x+40, self.top+40), "π", font=self.fonts.get('logo'), fill="white")

    def _show_fallback_logo(self):
        """Show fallback logo when image loading fails"""
        self._show_fallback_logo_with_text("Pi-hole")
