# Pi-hole Stats Display

A Python application that displays Pi-hole statistics and system information on a small OLED display (128x64). Perfect for monitoring your Pi-hole's performance at a glance.

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- [SH1106 OLED Display (128x64 pixels)](https://a.co/d/gTUvztw)
- [I2C connection between Pi and display](https://a.co/d/gRhyNK5)
- (optional) [pi/screen rack mount](https://www.printables.com/model/211251-19-raspberry-pi-34-rackmount-with-13-oled-screen-p)

### Display Wiring

| OLED Display | Raspberry Pi |
|--------------|--------------|
| VCC          | 3.3V (Pin 1) |
| GND          | Ground (Pin 6) |
| SCL          | GPIO3 (Pin 5) |
| SDA          | GPIO2 (Pin 3) |

## Software Requirements

- Python 3.7+
- Pi-hole with API access
- I2C enabled on Raspberry Pi

## Installation

You can install this application using the automated setup script (recommended) or manually.

### Prerequisite: Configure Pi-hole Application Password

Before installation, you need to set up your Pi-hole application password as an environment variable.

#### Get Your Pi-hole Application Password

1. Open your Pi-hole admin interface
1. Go to **Settings** → **Web Interface/API**
1. Toggle `Expert` option
1. Click **Configure App Password**
1. Copy the new app password
1. Click **Enable New App Password**

#### Set Environment Variable

Add the password to your environment:

```bash
export PIHOLE_APP_PASSWORD="your_application_password_here"

# To make it permanent, add to ~/.bashrc:
echo 'export PIHOLE_APP_PASSWORD="your_application_password_here"' >> ~/.bashrc
source ~/.bashrc

# Verify it's set
echo $PIHOLE_APP_PASSWORD
```

### Automated Setup (Recommended)

The project includes a comprehensive setup script that handles installation with security best practices:

```bash
cd /home/pi
git clone https://github.com/EmmanuelPineiro/SH1106-PiHole-Statistics.git stats
cd stats

# Run setup (this installs the service)
chmod +x deployment/setup.sh
sudo deployment/setup.sh

# Fix the service password configuration
chmod +x deployment/configure-password.sh
./deployment/configure-password.sh
```

The setup script will:
- Create a dedicated system user for security
- Install system dependencies  
- Set up Python environment
- Configure proper file permissions
- Create systemd service

The configure-password script will:
- Transfer your password from your environment to the systemd service
- Start the service
- Verify it's working


### Manual Setup
If you prefer manual installation, follow these steps:

#### 1. Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
sudo reboot
```

#### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install python3-pip python3-dev python3-pil i2c-tools
```

#### 3. Verify I2C Connection

```bash
sudo i2cdetect -y 1
# You should see your display address (usually 0x3c)
```

#### 4. Clone/Download the Project

```bash
cd /home/pi
git clone <your-repo-url> stats
# OR download and extract the files to a 'stats' directory
cd stats
```

#### 5. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

The project includes a `requirements.txt` file with the following dependencies:

```
luma.oled==3.12.0
luma.core==2.4.2
Pillow==10.0.1
requests==2.31.0
gpiozero==1.6.2
urllib3==2.0.7
cryptography==41.0.7
```

#### 6. Configure the Application

Edit `config.json` to match your setup:

```json
{
  "pihole": {
    "base_url": "https://your-pihole-ip/api/",
    "timeout": 10
  },
  "display": {
    "screen_display_time": 10,
    "logo_display_time": 5,
    "width": 128,
    "height": 64,
    "i2c_port": 1,
    "i2c_address": "0x3C"
  }
}
```

**Important Configuration Notes:**
- Change `your-pihole-ip` to your Pi-hole's actual IP address
- If Pi-hole is on the same device, use `localhost`
- Use `http://` instead of `https://` if Pi-hole doesn't have SSL
- Adjust `i2c_address` if your display uses a different address (check with `i2cdetect`)
- The application requires the `PIHOLE_APP_PASSWORD` environment variable to be set

**Security Note:** The configuration file contains sensitive settings. The application will warn if file permissions are not secure (should be 600).

#### 7. Test the Installation

```bash
python3 run.py
```

If everything is configured correctly, you should see screens cycling through:
1. **Ads Blocked**: Large percentage and count
2. **Network Stats**: IP address and Pi-hole statistics
3. **Hardware Info**: CPU, RAM, disk usage, and temperature  
4. **Logo**: Custom image or π symbol

**Note:** If you used the automated setup script, the application will already be running as a service at `/opt/pihole-stats/`. Check its status with:
```bash
sudo systemctl status pihole-stats.service
```

For manual installations, the application can be run directly:
```bash
python3 run.py
```

## Configuration Options

### QR code
- `qr_code.url`: URL the QR code screen will point to

### Log level
- `logging.level`: Log level to use (default: `INFO`)

### Display Settings

- `screen_display_time`: Seconds to show each main screen (default: 10)
- `logo_display_time`: Seconds to show logo screen (default: 5)  
- `width`, `height`: Display resolution (default: 128x64)
- `i2c_port`: I2C port number (default: 1)
- `i2c_address`: Display I2C address (default: 0x3C)

### Font Settings

- `mono_font_path`: Path to monospace font file
- `display_font_path`: Path to display/logo font file
- `sizes`: Font sizes for different text elements

### Screen Configuration

The `screens` array defines which screens to show and in what order:

```json
"screens": [
  {
    "name": "ads_blocked",
    "function": "show_ads_blocked_screen", 
    "duration": "screen_display_time",
    "requires_pihole_data": true
  }
]
```

## Running as a Service

The automated setup script creates and enables a systemd service automatically. The service runs the application continuously in the background.

### Managing the Service

You can manage the service with these commands:

```bash
# Check service status
sudo systemctl status pihole-stats.service

# Start the service
sudo systemctl start pihole-stats.service

# Stop the service
sudo systemctl stop pihole-stats.service

# Restart the service
sudo systemctl restart pihole-stats.service

# View recent logs
sudo journalctl -u pihole-stats.service -n 50

# Follow logs in real time
sudo journalctl -u pihole-stats.service -f

# Check application logs (file-based logging)
sudo tail -f /opt/pihole-stats/stats.log
```

## Adding Custom Screens

1. Add a new method to `DisplayManager` class in `display/display_manager.py`
2. Add screen configuration to `config.json`
3. Restart the application

## Troubleshooting

### Common Issues

**Display not working:**
```bash
# Check I2C is enabled
sudo raspi-config

# Check display is detected  
sudo i2cdetect -y 1

# Check permissions
sudo usermod -a -G i2c pi
```

**Authentication errors:**
```bash
# Verify environment variable is set
echo $PIHOLE_APP_PASSWORD

# Re-run the password configuration script
cd /path/to/SH1106-PiHole-Statistics/deployment
./configure-password.sh

# Check for authentication lockout in logs
sudo tail -f /opt/pihole-stats/stats.log | grep -i auth
```

**Service showing "Auth Failed retrying...":**
This usually means the password isn't reaching the service properly. Run:
```bash
cd /path/to/SH1106-PiHole-Statistics/deployment
./configure-password.sh
```

**IP address not showing:**
The system now uses multiple methods to detect IP, including a socket-based method that works in systemd restricted environments. Check logs for IP detection details:
```bash
sudo journalctl -u pihole-stats.service | grep -i ip
```

**Import errors:**
```bash
# Install missing packages
pip3 install luma.oled pillow requests gpiozero
```

**Permission errors:**
```bash
# Add user to required groups
sudo usermod -a -G gpio,i2c pi
```

### Log Files

The application uses both systemd journal logging and file-based logging:

```bash
# View systemd service logs
sudo journalctl -u pihole-stats.service -f

# View application logs (more detailed)
sudo tail -f /opt/pihole-stats/stats.log

# Check for specific issues
sudo grep -i "auth\|error\|ip" /opt/pihole-stats/stats.log
```