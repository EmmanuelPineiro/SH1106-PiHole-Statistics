import logging
import subprocess
from gpiozero import CPUTemperature

class SystemInfo:
    """System information utilities"""
    
    @staticmethod
    def get_ip_address():
        try:
            # Try multiple methods to get IP address
            methods = [
                "hostname -I | cut -d' ' -f1",
                "ip route get 1.1.1.1 | head -1 | awk '{print $7}'",
                "ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1"
            ]
            
            for cmd in methods:
                try:
                    result = subprocess.check_output(cmd, shell=True, timeout=5).decode('UTF-8').strip()
                    if result and result != '':
                        logging.debug(f"Got IP address using '{cmd}': {result}")
                        return result
                except Exception as e:
                    logging.debug(f"IP method '{cmd}' failed: {e}")
                    continue
            
            logging.warning("All IP address methods failed")
            return "No IP Found"
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
