import logging
import subprocess
from gpiozero import CPUTemperature

class SystemInfo:
    """System information utilities"""
    
    @staticmethod
    def get_ip_address():
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
