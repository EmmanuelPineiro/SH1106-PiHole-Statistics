import logging
import subprocess
from gpiozero import CPUTemperature

class SystemInfo:
    """System information utilities"""
    
    @staticmethod
    def get_ip_address():
        try:
            cmd = "hostname -I | cut -d' ' -f1"
            return subprocess.check_output(cmd, shell=True).decode('UTF-8').strip()
        except Exception:
            return "Unknown"
    
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
