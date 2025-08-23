#!/bin/bash

# Pi-hole Stats Display Setup Script
# Run this script to set up the application on a Raspberry Pi

create_dedicated_user() {
    echo "🔒 Setting up dedicated user for enhanced security..."
    
    DEDICATED_USER="pihole-stats"
    INSTALL_DIR="/opt/pihole-stats"
    
    # Check if user already exists
    if id "$DEDICATED_USER" &>/dev/null; then
        echo "✅ User $DEDICATED_USER already exists"
    else
        # Create system user (no login shell, no home directory creation)
        if sudo useradd -r -s /bin/false -d "$INSTALL_DIR" "$DEDICATED_USER"; then
            echo "✅ Created system user: $DEDICATED_USER"
        else
            echo "❌ Failed to create user $DEDICATED_USER"
            return 1
        fi
    fi
    
    # Add user to required groups
    echo "👤 Adding $DEDICATED_USER to required groups..."
    sudo usermod -a -G i2c,gpio "$DEDICATED_USER"
    
    # Create installation directory
    if [ ! -d "$INSTALL_DIR" ]; then
        if sudo mkdir -p "$INSTALL_DIR"; then
            echo "✅ Created installation directory: $INSTALL_DIR"
        else
            echo "❌ Failed to create installation directory"
            return 1
        fi
    fi
    
    # Copy application files to dedicated directory
    echo "📁 Copying application files to $INSTALL_DIR..."
    if sudo cp -r . "$INSTALL_DIR/"; then
        echo "✅ Files copied successfully"
    else
        echo "❌ Failed to copy application files"
        return 1
    fi
    
    # Set proper ownership and permissions
    echo "🔒 Setting secure file ownership and permissions..."
    sudo chown -R "$DEDICATED_USER:$DEDICATED_USER" "$INSTALL_DIR"
    
    # Set secure permissions
    sudo chmod 755 "$INSTALL_DIR"
    sudo chmod 644 "$INSTALL_DIR"/*.py "$INSTALL_DIR"/config/*.py "$INSTALL_DIR"/display/*.py "$INSTALL_DIR"/fonts/*.py "$INSTALL_DIR"/pihole/*.py "$INSTALL_DIR"/utils/*.py 2>/dev/null
    sudo chmod 755 "$INSTALL_DIR"/main.py
    sudo chmod 600 "$INSTALL_DIR"/config.json 2>/dev/null
    sudo chmod 600 "$INSTALL_DIR"/stats.log 2>/dev/null
    sudo chmod 644 "$INSTALL_DIR"/requirements.txt "$INSTALL_DIR"/README.md "$INSTALL_DIR"/SECURITY.md "$INSTALL_DIR"/*.service.template 2>/dev/null
    
    echo "✅ Dedicated user setup complete"
    return 0
}

setup_service() {
    echo "🔧 Setting up systemd service..."
    
    # Check if we're using dedicated user setup
    if [ "$USE_DEDICATED_USER" = true ]; then
        SERVICE_USER="pihole-stats"
        WORKING_DIR="/opt/pihole-stats"
        
        # Validate installation directory exists
        if [ ! -f "$WORKING_DIR/main.py" ] || [ ! -f "$WORKING_DIR/config.json" ]; then
            echo "❌ Error: Application files not found in $WORKING_DIR"
            return 1
        fi
    else
        # Validate we're in the right directory
        if [ ! -f "main.py" ] || [ ! -f "config.json" ]; then
            echo "❌ Error: main.py or config.json not found in current directory"
            echo "   Please run this script from the application directory"
            return 1
        fi
        
        # Get current directory and user
        WORKING_DIR=$(pwd)
        SERVICE_USER=$(whoami)
        
        # Don't run service as root
        if [ "$SERVICE_USER" = "root" ]; then
            echo "❌ Error: Cannot set up service to run as root for security reasons"
            echo "   Please run this script as a regular user (not with sudo)"
            return 1
        fi
    fi
    
    # Ask for Pi-hole password if not set
    if [ -z "$PIHOLE_APP_PASSWORD" ]; then
        echo ""
        echo "To set up the service, we need your Pi-hole application password."
        echo "Get it from: Pi-hole admin → Settings → API → Show API Token"
        echo ""
        read -s -p "Enter your Pi-hole application password: " PIHOLE_PASSWORD
        echo
        if [ -z "$PIHOLE_PASSWORD" ]; then
            echo "❌ No password provided. Service setup cancelled."
            return 1
        fi
        
        # Basic validation of password format
        if [ ${#PIHOLE_PASSWORD} -lt 32 ]; then
            echo "⚠️  Warning: Password seems too short for a Pi-hole application password"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "❌ Service setup cancelled."
                return 1
            fi
        fi
    else
        PIHOLE_PASSWORD="$PIHOLE_APP_PASSWORD"
    fi
    
    # Create service file from template
    SERVICE_FILE="/tmp/pihole-stats.service"
    TEMPLATE_FILE="pihole-stats.service.template"
    
    # Check if template exists
    if [ "$USE_DEDICATED_USER" = true ]; then
        TEMPLATE_PATH="/opt/pihole-stats/$TEMPLATE_FILE"
    else
        TEMPLATE_PATH="./$TEMPLATE_FILE"
    fi
    
    if [ ! -f "$TEMPLATE_PATH" ]; then
        echo "❌ Service template file not found: $TEMPLATE_PATH"
        return 1
    fi
    
    # Create service file by substituting variables in template
    sed -e "s|{{SERVICE_USER}}|$SERVICE_USER|g" \
        -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
        -e "s|{{PIHOLE_PASSWORD}}|$PIHOLE_PASSWORD|g" \
        "$TEMPLATE_PATH" > "$SERVICE_FILE"
    
    # Install service file
    if sudo mv "$SERVICE_FILE" /etc/systemd/system/pihole-stats.service; then
        echo "✅ Service file installed"
    else
        echo "❌ Failed to install service file"
        return 1
    fi
    
    # Set proper permissions
    sudo chmod 644 /etc/systemd/system/pihole-stats.service
    
    # Reload systemd and enable service
    echo "🔄 Reloading systemd and enabling service..."
    if sudo systemctl daemon-reload; then
        echo "✅ Systemd reloaded"
    else
        echo "❌ Failed to reload systemd"
        return 1
    fi
    
    if sudo systemctl enable pihole-stats.service; then
        echo "✅ Service enabled for auto-start on boot"
    else
        echo "❌ Failed to enable service"
        return 1
    fi
    
    # Ask if user wants to start the service now
    echo ""
    read -p "🚀 Would you like to start the service now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if sudo systemctl start pihole-stats.service; then
            echo "✅ Service started successfully!"
            sleep 2
            echo ""
            echo "📊 Service status:"
            sudo systemctl status pihole-stats.service --no-pager -l
        else
            echo "❌ Failed to start service"
            echo "   Check logs with: sudo journalctl -u pihole-stats -f"
            return 1
        fi
    fi
    
    echo ""
    echo "✅ Service setup complete!"
    echo "   • Service will start automatically on boot"
    echo "   • Use 'sudo systemctl start pihole-stats' to start manually"
    echo "   • Use 'sudo systemctl stop pihole-stats' to stop"
    echo "   • Use 'sudo systemctl status pihole-stats' to check status"
    echo "   • Use 'sudo journalctl -u pihole-stats -f' to view logs"
}

echo "Pi-hole Stats Display - Setup Script"
echo "===================================="

# Check if we have sudo privileges (needed for service installation)
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  This script requires sudo privileges for system setup."
    echo "You may be prompted for your password during installation."
    echo ""
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y python3-pip python3-dev python3-pil i2c-tools

# Enable I2C
echo "🔌 Enabling I2C..."
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
fi

# Add user to groups
echo "👤 Adding user to required groups..."
sudo usermod -a -G i2c,gpio $USER

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check for config file
if [ ! -f "config.json" ]; then
    echo "⚠️  config.json not found!"
    echo "Please make sure config.json exists and is properly configured."
    echo "See README.md for configuration details."
fi

# Check for PIHOLE_APP_PASSWORD
if [ -z "$PIHOLE_APP_PASSWORD" ]; then
    echo "⚠️  PIHOLE_APP_PASSWORD environment variable not set!"
    echo ""
    echo "To set your Pi-hole application password:"
    echo "1. Get your application password from Pi-hole admin → Settings → API"
    echo "2. Run: export PIHOLE_APP_PASSWORD=\"your_password_here\""
    echo "3. Add to ~/.bashrc to make permanent"
fi

# Set secure permissions on config file if it exists
if [ -f "config.json" ]; then
    echo "🔒 Setting secure permissions on config.json..."
    chmod 600 config.json
fi

# Test I2C
echo "🔍 Testing I2C connection..."
if command -v i2cdetect >/dev/null 2>&1; then
    echo "I2C devices found:"
    sudo i2cdetect -y 1
    echo "Look for your display address (usually 0x3c)"
else
    echo "⚠️  i2cdetect not available"
fi

# Ask about security setup
echo ""
echo "🔒 Security Setup Options"
echo "========================="
echo ""
echo "For enhanced security, you can:"
echo "1. Run as current user ($USER) - Standard setup"
echo "2. Create dedicated system user - Enhanced security (Recommended)"
echo ""
echo "The dedicated user option:"
echo "• Creates 'pihole-stats' system user (no login capability)"
echo "• Installs app to /opt/pihole-stats with proper permissions"  
echo "• Provides better isolation and security"
echo ""
read -p "Choose setup type (1=current user, 2=dedicated user): " -n 1 -r
echo

USE_DEDICATED_USER=false
if [[ $REPLY == "2" ]]; then
    if create_dedicated_user; then
        USE_DEDICATED_USER=true
        echo "✅ Dedicated user setup completed successfully"
    else
        echo "❌ Dedicated user setup failed, falling back to current user"
        USE_DEDICATED_USER=false
    fi
elif [[ $REPLY == "1" ]]; then
    echo "📝 Using current user setup"
    USE_DEDICATED_USER=false
else
    echo "📝 Invalid choice, defaulting to current user setup"
    USE_DEDICATED_USER=false
fi

# Ask if user wants to set up as a service
echo ""
read -p "🚀 Would you like to set up Pi-hole Stats Display as a system service? (y/N): " -n 1 -r
echo
SERVICE_SETUP_SUCCESS=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if setup_service; then
        SERVICE_SETUP_SUCCESS=true
    else
        echo "❌ Service setup failed. You can set it up manually later."
        echo "   See README.md for manual service setup instructions."
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""

if [ "$SERVICE_SETUP_SUCCESS" = true ]; then
    echo "🎉 Your Pi-hole Stats Display is now set up as a system service!"
    echo ""
    if [ "$USE_DEDICATED_USER" = true ]; then
        echo "🔒 Security Features:"
        echo "• Running as dedicated 'pihole-stats' user"
        echo "• Installed in secure location: /opt/pihole-stats"
        echo "• Enhanced systemd security features enabled"
        echo ""
        echo "Final steps:"
        echo "1. Configure /opt/pihole-stats/config.json with your Pi-hole details"
        echo "2. Reboot your Pi to ensure all changes take effect: sudo reboot"
        echo "3. After reboot, check service status: sudo systemctl status pihole-stats"
    else
        echo "Final steps:"
        echo "1. Configure config.json with your Pi-hole details if not already done"
        echo "2. Reboot your Pi to ensure all changes take effect: sudo reboot"
        echo "3. After reboot, check service status: sudo systemctl status pihole-stats"
    fi
    echo ""
    echo "Service management commands:"
    echo "• View logs: sudo journalctl -u pihole-stats -f"
    echo "• Restart: sudo systemctl restart pihole-stats"
    echo "• Stop: sudo systemctl stop pihole-stats"
elif [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Service setup was attempted but failed."
    echo ""
    echo "Next steps:"
    if [ "$USE_DEDICATED_USER" = true ]; then
        echo "1. Set PIHOLE_APP_PASSWORD for pihole-stats user"
        echo "2. Configure /opt/pihole-stats/config.json with your Pi-hole details"
        echo "3. Test manually: sudo -u pihole-stats python3 /opt/pihole-stats/main.py"
    else
        echo "1. Set PIHOLE_APP_PASSWORD environment variable"
        echo "2. Configure config.json with your Pi-hole details"
        echo "3. Test manually: python3 main.py"
    fi
    echo "4. Set up service manually (see README.md)"
    echo "5. Reboot your Pi: sudo reboot"
else
    echo "📝 Service setup skipped."
    echo ""
    echo "Next steps:"
    if [ "$USE_DEDICATED_USER" = true ]; then
        echo "1. Set PIHOLE_APP_PASSWORD for pihole-stats user"
        echo "2. Configure /opt/pihole-stats/config.json with your Pi-hole details"
        echo "3. Test manually: sudo -u pihole-stats python3 /opt/pihole-stats/main.py"
        echo "4. Set up service manually later (see README.md)"
    else
        echo "1. Set PIHOLE_APP_PASSWORD environment variable"
        echo "2. Configure config.json with your Pi-hole details"  
        echo "3. Test manually: python3 main.py"
        echo "4. Set up service manually later (see README.md)"
    fi
    echo "5. Reboot your Pi: sudo reboot"
fi
echo ""
if [ "$USE_DEDICATED_USER" = true ]; then
    echo "📝 Security Note:"
    echo "   Your app is now running with enhanced security using a dedicated system user."
    echo "   The 'pihole-stats' user has minimal privileges and cannot log in to the system."
    echo ""
fi
echo "📖 For detailed instructions, see README.md"cho "🔒 For security best practices, see SECURITY.md"
