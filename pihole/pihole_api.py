import os
import logging
import requests
import time
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class PiholeAPI:
    """Handle Pi-hole API interactions with security enhancements"""
    def __init__(self, config):
        self.config = config
        self.base_url = config.get('pihole.base_url')
        self.timeout = min(config.get('pihole.timeout', 10), 30)  # Cap timeout at 30s
        self.session_data = {'sid': None, 'csrf': None}
        self.last_auth_attempt = 0
        self.auth_failures = 0
        self.max_auth_failures = 5
        self.rate_limit_delay = 1  # seconds between requests
        self.last_request_time = 0
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Disable SSL warnings for local connections but log them
        if 'localhost' in self.base_url or '127.0.0.1' in self.base_url:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logging.info("SSL verification disabled for localhost connection")
    
    def authenticate(self):
        # Rate limiting for authentication attempts
        current_time = time.time()
        if current_time - self.last_auth_attempt < 5:  # 5 second cooldown
            logging.warning("Authentication rate limited")
            return False
        
        # Check for too many failures
        if self.auth_failures >= self.max_auth_failures:
            if current_time - self.last_auth_attempt < 300:  # 5 minute lockout
                logging.error("Too many authentication failures, locked out")
                return False
            else:
                self.auth_failures = 0  # Reset after lockout period
        
        self.last_auth_attempt = current_time
        
        password = os.getenv('PIHOLE_APP_PASSWORD')
        if not password:
            logging.error("PIHOLE_APP_PASSWORD environment variable not set")
            return False
        
        # Validate password format (Pi-hole app passwords are base64-like)
        if len(password) < 32 or not password.replace('=', '').replace('+', '').replace('/', '').isalnum():
            logging.error("Invalid password format")
            self.auth_failures += 1
            return False
        
        try:
            url = urljoin(self.base_url, "auth")
            
            # Rate limiting
            self._rate_limit()
            
            response = self.session.post(
                url, 
                json={"password": password}, 
                verify=False, 
                timeout=self.timeout,
                headers={'User-Agent': 'PiHole-Stats-Display/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "session" in data and "sid" in data["session"] and "csrf" in data["session"]:
                    self.session_data['sid'] = data["session"]["sid"]
                    self.session_data['csrf'] = data["session"]["csrf"]
                    self.auth_failures = 0  # Reset on success
                    logging.info("Authentication successful")
                    return True
                else:
                    logging.error("Invalid authentication response structure")
            
            logging.error(f"Authentication failed: {response.status_code}")
            self.auth_failures += 1
            return False
            
        except requests.exceptions.Timeout:
            logging.error("Authentication timeout")
            self.auth_failures += 1
            return False
        except requests.exceptions.ConnectionError:
            logging.error("Connection error during authentication")
            self.auth_failures += 1
            return False
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            self.auth_failures += 1
            return False
    
    def get_stats(self):
        if not self.session_data['sid'] or not self.session_data['csrf']:
            return None
        
        try:
            headers = {
                "X-FTL-SID": self.session_data['sid'],
                "X-FTL-CSRF": self.session_data['csrf'],
                "User-Agent": "PiHole-Stats-Display/1.0"
            }
            
            # Validate session tokens
            if not self._validate_session_tokens():
                logging.warning("Invalid session tokens detected")
                self.session_data = {'sid': None, 'csrf': None}
                return None
            
            url = urljoin(self.base_url, "stats/summary")
            
            # Rate limiting
            self._rate_limit()
            
            response = self.session.get(
                url, 
                headers=headers, 
                verify=False, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                # Validate response data
                if self._validate_stats_data(data):
                    return data
                else:
                    logging.warning("Invalid stats data received")
                    return None
            elif response.status_code == 401:
                # Session expired
                logging.info("Session expired, need to re-authenticate")
                self.session_data = {'sid': None, 'csrf': None}
            else:
                logging.error(f"API request failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logging.error("API request timeout")
        except requests.exceptions.ConnectionError:
            logging.error("Connection error during API request")
        except Exception as e:
            logging.error(f"Error getting stats: {e}")
        
        return None
    
    def _rate_limit(self):
        """Implement simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _validate_session_tokens(self):
        """Validate session token format"""
        sid = self.session_data.get('sid', '')
        csrf = self.session_data.get('csrf', '')
        
        # Basic validation - tokens should be non-empty strings
        if not isinstance(sid, str) or not isinstance(csrf, str):
            return False
        if len(sid) < 10 or len(csrf) < 10:  # Reasonable minimum length
            return False
        
        return True
    
    def _validate_stats_data(self, data):
        """Validate Pi-hole stats data structure"""
        if not isinstance(data, dict):
            return False
        
        # Check for expected fields and reasonable values
        expected_fields = ['ads_percentage_today', 'ads_blocked_today', 'dns_queries_today']
        for field in expected_fields:
            if field not in data:
                return False
            
            value = data[field]
            if field == 'ads_percentage_today':
                try:
                    float_val = float(value)
                    if float_val < 0 or float_val > 100:
                        logging.warning(f"Suspicious percentage value: {float_val}")
                        return False
                except (ValueError, TypeError):
                    return False
            elif field in ['ads_blocked_today', 'dns_queries_today']:
                try:
                    int_val = int(value)
                    if int_val < 0 or int_val > 10000000:  # Reasonable upper limit
                        logging.warning(f"Suspicious count value: {int_val}")
                        return False
                except (ValueError, TypeError):
                    return False
        
        return True
