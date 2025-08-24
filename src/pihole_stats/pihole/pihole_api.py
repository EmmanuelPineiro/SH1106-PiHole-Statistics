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
        self.logger = logging.getLogger(self.__class__.__name__)
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
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                self.logger.info("SSL verification disabled for localhost connection")
            except ImportError:
                self.logger.debug("urllib3 not available for SSL warning suppression")
    
    def authenticate(self):
        # Rate limiting for authentication attempts
        current_time = time.time()
        if current_time - self.last_auth_attempt < 5:  # 5 second cooldown
            self.logger.warning("Authentication rate limited")
            return False
        
        # Check for too many failures
        if self.auth_failures >= self.max_auth_failures:
            if current_time - self.last_auth_attempt < 300:  # 5 minute lockout
                self.logger.error("Too many authentication failures, locked out")
                return False
            else:
                self.auth_failures = 0  # Reset after lockout period
        
        self.last_auth_attempt = current_time
        
        password = os.getenv('PIHOLE_APP_PASSWORD')
        if not password:
            self.logger.error("PIHOLE_APP_PASSWORD environment variable not set")
            return False
        
        # Validate password format (Pi-hole app passwords are base64-like)
        if len(password) < 32 or not password.replace('=', '').replace('+', '').replace('/', '').isalnum():
            self.logger.error("Invalid password format")
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
                    self.logger.info("Authentication successful")
                    return True
                else:
                    self.logger.error("Invalid authentication response structure")
            
            self.logger.error(f"Authentication failed: {response.status_code}")
            self.auth_failures += 1
            return False
            
        except requests.exceptions.Timeout:
            self.logger.error("Authentication timeout")
            self.auth_failures += 1
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error("Connection error during authentication")
            self.auth_failures += 1
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
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
                self.logger.warning("Invalid session tokens detected")
                self.session_data = {'sid': None, 'csrf': None}
                return None
            
            url = urljoin(self.base_url, "stats/summary")
            
            # Rate limiting
            self._rate_limit()
            
            self.logger.debug(f"Making API request to {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                verify=False, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.debug("API response received successfully")
                # Validate response data
                if self._validate_stats_data(data):
                    return data
                else:
                    self.logger.warning("Invalid stats data received")
                    self.logger.debug(f"Received data: {data}")
                    return None
            elif response.status_code == 401:
                # Session expired
                self.logger.info("Session expired, need to re-authenticate")
                self.session_data = {'sid': None, 'csrf': None}
            else:
                self.logger.error(f"API request failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.logger.error("API request timeout")
        except requests.exceptions.ConnectionError:
            self.logger.error("Connection error during API request")
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
        
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
            self.logger.warning("Stats data is not a dictionary")
            return False
        
        # Check for expected top-level fields in the new API format
        required_sections = ['queries', 'clients', 'gravity']
        for section in required_sections:
            if section not in data:
                self.logger.warning(f"Missing required section: {section}")
                return False
        
        # Validate queries section
        queries = data.get('queries', {})
        if not isinstance(queries, dict):
            self.logger.warning("Queries section is not a dictionary")
            return False
        
        # Check for essential query fields
        query_fields = ['total', 'blocked', 'percent_blocked']
        for field in query_fields:
            if field not in queries:
                self.logger.warning(f"Missing query field: {field}")
                return False
            
            value = queries[field]
            if field == 'percent_blocked':
                try:
                    float_val = float(value)
                    if float_val < 0 or float_val > 100:
                        self.logger.warning(f"Suspicious percentage value: {float_val}")
                        return False
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid percentage format: {value}")
                    return False
            elif field in ['total', 'blocked']:
                try:
                    int_val = int(value)
                    if int_val < 0 or int_val > 100000000:  # Reasonable upper limit
                        self.logger.warning(f"Suspicious count value: {int_val}")
                        return False
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid count format: {value}")
                    return False
        
        # Validate clients section
        clients = data.get('clients', {})
        if not isinstance(clients, dict):
            self.logger.warning("Clients section is not a dictionary")
            return False
        
        if 'total' not in clients or 'active' not in clients:
            self.logger.warning("Missing client count fields")
            return False
        
        # Validate gravity section
        gravity = data.get('gravity', {})
        if not isinstance(gravity, dict):
            self.logger.warning("Gravity section is not a dictionary")
            return False
        
        if 'domains_being_blocked' not in gravity:
            self.logger.warning("Missing gravity domains count")
            return False
        
        self.logger.debug("Stats data validation passed")
        return True
