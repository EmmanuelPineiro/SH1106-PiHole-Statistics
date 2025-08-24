# Deployment Scripts

This directory contains scripts for deploying and managing the Pi-hole OLED Statistics Display on Raspberry Pi systems.

## Scripts

### `deploy.sh` - Main Deployment Script

Automatically installs and configures the Pi-hole statistics display as a systemd service.

**Features:**
- ✅ Installs all required system dependencies
- ✅ Enables I2C interface
- ✅ Creates dedicated user and secure directories
- ✅ Installs Python dependencies in virtual environment
- ✅ Creates and enables systemd service
- ✅ Configures security settings
- ✅ Tests I2C connection
- ✅ Comprehensive logging

**Usage:**
```bash
sudo ./deploy.sh
```

### `uninstall.sh` - Removal Script

Completely removes the Pi-hole statistics display from the system.

**Features:**
- ✅ Stops and removes systemd service
- ✅ Removes all application files
- ✅ Cleans up user and directories
- ✅ Removes log files
- ✅ Confirmation prompt for safety

**Usage:**
```bash
sudo ./uninstall.sh
```

### `configure-password.sh` - Service Password Fix

Simple script to transfer your Pi-hole password from your environment to the systemd service.

**Usage:**
```bash
# After setting PIHOLE_APP_PASSWORD in your .bashrc
./configure-password.sh
```

## Installation Process

The deployment script performs these steps:

1. **System Preparation**
   - Verifies Raspberry Pi environment
   - Updates package lists
   - Installs system dependencies (Python, I2C tools, build essentials)

2. **I2C Configuration**
   - Enables I2C in boot config
   - Loads I2C kernel modules
   - Adds modules to boot sequence

3. **Application Setup**
   - Creates dedicated `pi` user
   - Creates secure installation directory `/opt/pihole-stats`
   - Copies all application files
   - Sets proper permissions and ownership

4. **Python Environment**
   - Creates isolated virtual environment
   - Installs Python dependencies from `requirements.txt`
   - Sets up proper paths and permissions

5. **Service Configuration**
   - Creates systemd service file
   - Enables security hardening options
   - Starts and enables the service
   - Verifies service status

6. **Testing & Verification**
   - Tests I2C bus connectivity
   - Checks service startup
   - Displays status and next steps

## Post-Installation

After successful deployment:

### **Setup Pi-hole Password**

1. **Add your Pi-hole password to your environment:**
   ```bash
   # Get your Pi-hole API token from: Pi-hole Admin > Settings > API
   echo 'export PIHOLE_APP_PASSWORD="your_pihole_password_here"' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Fix the service configuration:**
   ```bash
   cd /path/to/SH1106-PiHole-Statistics/deployment
   ./configure-password.sh
   ```

That's it! The service should now be running properly.

### Configuration
Edit the configuration file:
```bash
sudo nano /opt/pihole-stats/config.json
```

### Service Management
```bash
# View logs
sudo journalctl -u pihole-stats -f

# Check service status
sudo systemctl status pihole-stats

# Restart service
sudo systemctl restart pihole-stats

# Stop service
sudo systemctl stop pihole-stats
```

### I2C Testing
```bash
# Scan for I2C devices
sudo i2cdetect -y 1
```

## File Locations

After installation:

| Item | Location |
|------|----------|
| Application Files | `/opt/pihole-stats/` |
| Configuration | `/opt/pihole-stats/config.json` |
| Virtual Environment | `/opt/pihole-stats/venv/` |
| Service File | `/etc/systemd/system/pihole-stats.service` |
| Logs | `journalctl -u pihole-stats` |

## Security Features

The deployment includes security hardening:

- ✅ **Dedicated user** - Runs as non-root `pi` user
- ✅ **File permissions** - Restrictive file and directory permissions
- ✅ **Systemd security** - NoNewPrivileges, PrivateTmp, ProtectSystem
- ✅ **Path validation** - Secure path handling in application
- ✅ **Input sanitization** - Validates all user inputs

## Troubleshooting

### Service Won't Start
```bash
# Check detailed service status
sudo systemctl status pihole-stats -l

# View recent logs
sudo journalctl -u pihole-stats -n 50

# Check configuration syntax
python3 -c "import json; json.load(open('/opt/pihole-stats/config.json'))"
```

### Display Issues
```bash
# Test I2C connection
sudo i2cdetect -y 1

# Check I2C permissions
ls -la /dev/i2c-*

# Verify display address in config matches hardware
```

### Python Errors
```bash
# Test virtual environment
sudo -u pi /opt/pihole-stats/venv/bin/python3 -c "import luma.oled, qrcode, requests"

# Check Python path
sudo -u pi /opt/pihole-stats/venv/bin/python3 /opt/pihole-stats/run.py --test
```

## Requirements

- **Hardware**: Raspberry Pi with I2C-compatible OLED display (SH1106)
- **OS**: Raspberry Pi OS (Bullseye or newer recommended)
- **Network**: Access to Pi-hole API
- **Permissions**: Root access for installation

## Compatibility

Tested on:
- Raspberry Pi 3B+, 4B, Zero 2 W
- Raspberry Pi OS Bullseye/Bookworm
- SH1106 1.3" OLED displays
- Pi-hole v5.x and v6.x
