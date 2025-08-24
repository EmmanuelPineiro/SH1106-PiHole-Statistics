import logging
import subprocess
from gpiozero import CPUTemperature

class SystemInfo:
    """System information utilities"""
    
    @staticmethod
    def get_ip_address():
        try:
            # Method 1: Read from /proc/net/route (works in restricted environments)
            try:
                with open('/proc/net/route', 'r') as f:
                    for line in f:
                        fields = line.strip().split()
                        if len(fields) >= 11 and fields[1] == '00000000':  # Default route
                            # Get interface name
                            interface = fields[0]
                            # Read IP from interface
                            cmd = f"cat /sys/class/net/{interface}/address 2>/dev/null || ip addr show {interface} | grep 'inet ' | head -1 | awk '{{print $2}}' | cut -d'/' -f1"
                            result = subprocess.check_output(cmd, shell=True, timeout=3).decode('UTF-8').strip()
                            if result and '.' in result:
                                logging.debug(f"Got IP from interface {interface}: {result}")
                                return result
            except Exception as e:
                logging.debug(f"Route method failed: {e}")

            # Method 2: Use ip command (usually works in systemd)
            try:
                cmd = "ip route get 1.1.1.1 2>/dev/null | head -1 | awk '{print $7}' 2>/dev/null"
                result = subprocess.check_output(cmd, shell=True, timeout=3).decode('UTF-8').strip()
                if result and result != '' and '.' in result:
                    logging.debug(f"Got IP using ip route: {result}")
                    return result
            except Exception as e:
                logging.debug(f"IP route method failed: {e}")
            
            # Method 3: Read /proc/net/fib_trie (fallback)
            try:
                import socket
                # Get local IP by connecting to a remote address
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("1.1.1.1", 80))
                    ip = s.getsockname()[0]
                    if ip and ip != '127.0.0.1':
                        logging.debug(f"Got IP using socket method: {ip}")
                        return ip
            except Exception as e:
                logging.debug(f"Socket method failed: {e}")

            # Method 4: Parse ip addr directly
            try:
                cmd = "ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1"
                result = subprocess.check_output(cmd, shell=True, timeout=3).decode('UTF-8').strip()
                if result and result != '' and '.' in result:
                    logging.debug(f"Got IP using ip addr: {result}")
                    return result
            except Exception as e:
                logging.debug(f"IP addr method failed: {e}")
            
            logging.warning("All IP address methods failed")
            return "No Network"
        except Exception as e:
            logging.error(f"Error getting IP address: {e}")
            return "IP Error"
    
    @staticmethod
    def get_hardware_info():
        try:
            cmd = "top -bn1 | grep load | awk '{printf \"%.2f\", $(NF-2)}'"
            cpu = subprocess.check_output(cmd, shell=True).decode('UTF-8')
            
            cmd = "free -m | awk 'NR==2{printf \"%s/%sMB\", $3,$2 }'"
            memory = subprocess.check_output(cmd, shell=True).decode('UTF-8')
            
            cmd = "df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'"
            disk = subprocess.check_output(cmd, shell=True).decode('UTF-8')
            
            cpu_temp = CPUTemperature()
            temp = round(cpu_temp.temperature, 1)
            
            return {'cpu_load': cpu, 'memory': memory, 'disk': disk, 'temperature': temp}
        except Exception as e:
            logging.error(f"Hardware info error: {e}")
            return None
