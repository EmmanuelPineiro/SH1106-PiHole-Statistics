#!/bin/bash

# Pi-hole OLED Statistics Display - Uninstall Script
# This script removes the Pi-hole statistics display from the system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="pihole-stats"
INSTALL_DIR="/opt/pihole-stats"
USER="pi"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

confirm_uninstall() {
    echo -e "${YELLOW}This will completely remove the Pi-hole OLED Statistics Display from your system.${NC}"
    echo
    echo "The following will be removed:"
    echo "• Service: $SERVICE_NAME"
    echo "• Installation directory: $INSTALL_DIR"
    echo "• System user: $USER (if no other services use it)"
    echo "• Log files"
    echo
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Uninstall cancelled by user"
        exit 0
    fi
}

stop_and_remove_service() {
    log "Stopping and removing service..."
    
    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
        info "Service stopped"
    fi
    
    # Disable service if enabled
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
        info "Service disabled"
    fi
    
    # Remove service file
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    if [ -f "$SERVICE_FILE" ]; then
        rm "$SERVICE_FILE"
        info "Service file removed"
    fi
    
    # Reload systemd
    systemctl daemon-reload
    systemctl reset-failed 2>/dev/null || true
    
    log "Service removed"
}

remove_installation_directory() {
    log "Removing installation directory..."
    
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        info "Installation directory removed: $INSTALL_DIR"
    else
        warning "Installation directory not found: $INSTALL_DIR"
    fi
}

remove_user() {
    log "Checking user removal..."
    
    if id "$USER" &>/dev/null; then
        # Check if user is used by other services
        if systemctl list-units --all | grep -v "$SERVICE_NAME" | grep -q "User=$USER"; then
            warning "User '$USER' is used by other services, not removing"
        else
            userdel "$USER" 2>/dev/null || true
            info "User '$USER' removed"
        fi
    else
        info "User '$USER' not found, nothing to remove"
    fi
}

remove_logs() {
    log "Removing log files..."
    
    # Remove specific log files
    LOG_FILES=(
        "/var/log/pihole-stats-deploy.log"
        "/var/log/pihole-stats.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            rm "$log_file"
            info "Removed log file: $log_file"
        fi
    done
    
    # Clean journal logs for the service
    journalctl --vacuum-time=1s --unit="$SERVICE_NAME" 2>/dev/null || true
}

show_completion() {
    echo
    echo -e "${GREEN}================================"
    echo -e "   UNINSTALL COMPLETED!"
    echo -e "================================${NC}"
    echo
    echo -e "${BLUE}What was removed:${NC}"
    echo "• Pi-hole OLED Statistics Display service"
    echo "• All application files and directories"
    echo "• Log files and journal entries"
    echo
    echo -e "${YELLOW}Note: I2C interface and system packages were left intact${NC}"
    echo -e "${YELLOW}Note: You may want to reboot to ensure all changes take effect${NC}"
    echo
}

# Main uninstall process
main() {
    log "Starting Pi-hole OLED Statistics Display uninstall..."
    
    # Pre-flight checks
    check_root
    confirm_uninstall
    
    # Uninstall process
    stop_and_remove_service
    remove_installation_directory
    remove_user
    remove_logs
    
    # Show completion info
    show_completion
    
    log "Uninstall completed successfully!"
}

# Handle script interruption
trap 'error "Uninstall interrupted"' INT TERM

# Run main function
main "$@"
