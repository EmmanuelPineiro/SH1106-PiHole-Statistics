#!/bin/bash

# Pi-hole OLED Statistics Display - Deployment Script
# This script automates the deployment of the Pi-hole statistics display on Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="pihole-stats"
SERVICE_NAME="pihole-stats"
INSTALL_DIR="/opt/pihole-stats"
USER="pi"
LOG_FILE="/var/log/pihole-stats-deploy.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    echo "[ERROR] $1" >> "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
    echo "[WARNING] $1" >> "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
    echo "[INFO] $1" >> "$LOG_FILE"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        warning "This doesn't appear to be a Raspberry Pi. Continuing anyway..."
    else
        log "Raspberry Pi detected"
    fi
}

install_system_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    apt-get update -y
    
    # Install required system packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        i2c-tools \
        git \
        curl \
        wget \
        build-essential \
        libfreetype6-dev \
        libjpeg-dev \
        libopenjp2-7 \
    
    log "System dependencies installed"
}

enable_i2c() {
    log "Enabling I2C interface..."
    
    # Enable I2C in config
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
        info "Added I2C to boot config"
    fi
    
    # Load I2C modules
    modprobe i2c-dev 2>/dev/null || true
    
    # Add to modules for boot
    if ! grep -q "^i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
        info "Added i2c-dev to boot modules"
    fi
    
    log "I2C interface enabled"
}

create_user_and_directories() {
    log "Setting up user and directories..."
    
    # Create user if it doesn't exist
    if ! id "$USER" &>/dev/null; then
        useradd -r -s /bin/false "$USER"
        info "Created user: $USER"
    fi
    
    # Add user to i2c group for hardware access
    if getent group i2c >/dev/null 2>&1; then
        usermod -a -G i2c "$USER" 2>/dev/null || true
        info "Added user $USER to i2c group"
    else
        # Create i2c group if it doesn't exist
        groupadd i2c 2>/dev/null || true
        usermod -a -G i2c "$USER" 2>/dev/null || true
        info "Created i2c group and added user $USER"
    fi
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Create log directory
    mkdir -p "/var/log"
    touch "$LOG_FILE"
    
    log "User and directories created"
}

copy_application_files() {
    log "Copying application files..."
    
    # Get the script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Copy all necessary files
    cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/config.json" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/run.py" "$INSTALL_DIR/"
    
    # Copy assets if they exist
    if [ -d "$PROJECT_ROOT/assets" ]; then
        cp -r "$PROJECT_ROOT/assets" "$INSTALL_DIR/"
    fi
    
    # Set ownership
    chown -R "$USER:$USER" "$INSTALL_DIR"
    
    # Set permissions
    chmod 755 "$INSTALL_DIR/run.py"
    find "$INSTALL_DIR" -type f -name "*.py" -exec chmod 644 {} \;
    find "$INSTALL_DIR" -type d -exec chmod 755 {} \;
    
    log "Application files copied"
}

install_python_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Activate virtual environment and install packages
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/requirements.txt"
    deactivate
    
    # Set ownership of virtual environment
    chown -R "$USER:$USER" "$INSTALL_DIR/venv"
    
    log "Python dependencies installed"
}

create_systemd_service() {
    log "Creating systemd service..."
    
    # Get the script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    TEMPLATE_FILE="$SCRIPT_DIR/pihole-stats.service.template"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    # Check if template exists
    if [ ! -f "$TEMPLATE_FILE" ]; then
        error "Service template not found: $TEMPLATE_FILE"
    fi
    
    # Create service file from template with variable substitution
    cp "$TEMPLATE_FILE" "$SERVICE_FILE"
    
    # Replace template variables
    sed -i "s|{{SERVICE_USER}}|$USER|g" "$SERVICE_FILE"
    sed -i "s|{{SERVICE_GROUP}}|$USER|g" "$SERVICE_FILE"
    sed -i "s|{{SERVICE_NAME}}|$SERVICE_NAME|g" "$SERVICE_FILE"
    sed -i "s|{{WORKING_DIR}}|$INSTALL_DIR|g" "$SERVICE_FILE"
    sed -i "s|{{PYTHON_PATH}}|$INSTALL_DIR/venv/bin/python3|g" "$SERVICE_FILE"
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log "Systemd service created and enabled"
}

configure_application() {
    log "Configuring application..."
    
    CONFIG_FILE="$INSTALL_DIR/config.json"
    
    # Update font paths in config to use absolute paths
    sed -i "s|\"./assets/|\"$INSTALL_DIR/assets/|g" "$CONFIG_FILE"
    
    # Ensure proper ownership
    chown "$USER:$USER" "$CONFIG_FILE"
    
    log "Application configured"
}

test_i2c_connection() {
    log "Testing I2C connection..."
    
    if command -v i2cdetect >/dev/null 2>&1; then
        info "Scanning I2C bus 1 for devices..."
        i2cdetect -y 1 || warning "No I2C devices detected on bus 1"
    else
        warning "i2cdetect not available, skipping I2C test"
    fi
}

start_service() {
    log "Starting service..."
    
    # First, let's test the application manually to see if there are any immediate errors
    info "Testing application startup manually..."
    if sudo -u "$USER" "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/run.py" --test 2>&1 | head -20; then
        info "Manual test completed - check output above for any errors"
    else
        warning "Manual test failed - this may indicate the issue"
    fi
    
    # Start the service
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for service to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Service started successfully"
        info "Service status:"
        systemctl status "$SERVICE_NAME" --no-pager -l
    else
        warning "Service failed to start. Gathering diagnostic information..."
        
        # Show recent logs with more detail
        info "Recent service logs:"
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager || true
        
        # Test Python environment
        info "Testing Python environment:"
        sudo -u "$USER" "$INSTALL_DIR/venv/bin/python3" -c "
import sys
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path}')
try:
    import luma.oled
    print('✓ luma.oled imported successfully')
except ImportError as e:
    print(f'✗ luma.oled import failed: {e}')
try:
    import qrcode
    print('✓ qrcode imported successfully')
except ImportError as e:
    print(f'✗ qrcode import failed: {e}')
try:
    import requests
    print('✓ requests imported successfully')
except ImportError as e:
    print(f'✗ requests import failed: {e}')
" 2>&1 || true
        
        # Check file permissions
        info "Checking file permissions:"
        ls -la "$INSTALL_DIR/" | head -10
        ls -la "$INSTALL_DIR/src/pihole_stats/" | head -5
        
        # Check I2C permissions
        info "Checking I2C permissions:"
        ls -la /dev/i2c-* 2>/dev/null || echo "No I2C devices found"
        groups "$USER" || true
        
        error "Service failed to start. Check the diagnostic information above."
    fi
}

cleanup() {
    log "Cleaning up temporary files..."
    # Remove any temporary files if needed
    log "Cleanup completed"
}

show_next_steps() {
    echo
    echo -e "${GREEN}================================"
    echo -e "   DEPLOYMENT COMPLETED!"
    echo -e "================================${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Edit the configuration file: $INSTALL_DIR/config.json"
    echo "2. Update Pi-hole URL and other settings as needed"
    echo "3. Restart the service: sudo systemctl restart $SERVICE_NAME"
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "• View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "• Check status: sudo systemctl status $SERVICE_NAME"
    echo "• Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "• Stop service: sudo systemctl stop $SERVICE_NAME"
    echo "• Test I2C: sudo i2cdetect -y 1"
    echo
    echo -e "${YELLOW}Configuration file location: $INSTALL_DIR/config.json${NC}"
    echo -e "${YELLOW}Installation directory: $INSTALL_DIR${NC}"
    echo
}

# Main deployment process
main() {
    log "Starting Pi-hole OLED Statistics Display deployment..."
    
    # Pre-flight checks
    check_root
    check_raspberry_pi
    
    # System setup
    install_system_dependencies
    enable_i2c
    
    # Application setup
    create_user_and_directories
    copy_application_files
    install_python_dependencies
    configure_application
    
    # Service setup
    create_systemd_service
    
    # Testing
    test_i2c_connection
    start_service
    
    # Cleanup
    cleanup
    
    # Show completion info
    show_next_steps
    
    log "Deployment completed successfully!"
}

# Handle script interruption
trap 'error "Deployment interrupted"' INT TERM

# Run main function
main "$@"
