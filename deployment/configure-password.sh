#!/bin/bash

# Simple Pi-hole password configuration for systemd service
# This script assumes you've already set PIHOLE_APP_PASSWORD in your environment

set -e

echo "🔧 Pi-hole Stats Display - Simple Password Fix"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "❌ Please don't run this script as root"
    exit 1
fi

# Check if password is set in current environment
if [ -z "$PIHOLE_APP_PASSWORD" ]; then
    echo "❌ PIHOLE_APP_PASSWORD not found in current environment"
    echo "   Make sure you've added: export PIHOLE_APP_PASSWORD=\"YOUR_PASSWORD\""
    echo "   to your ~/.bashrc and run: source ~/.bashrc"
    exit 1
fi

echo "✅ Found PIHOLE_APP_PASSWORD in environment"

# Check if service exists
if ! sudo systemctl is-enabled pihole-stats.service >/dev/null 2>&1; then
    echo "❌ pihole-stats.service not found. Please run setup.sh first"
    exit 1
fi

# Stop service if running
if systemctl is-active --quiet pihole-stats.service; then
    echo "⏸️  Stopping service..."
    sudo systemctl stop pihole-stats.service
fi

# Fix the service file
SERVICE_FILE="/etc/systemd/system/pihole-stats.service"

echo "🔧 Updating service file with your password..."

# Replace placeholder or add environment variable
if sudo grep -q "{{PIHOLE_PASSWORD}}" "$SERVICE_FILE"; then
    sudo sed -i "s|Environment=PIHOLE_APP_PASSWORD={{PIHOLE_PASSWORD}}|Environment=PIHOLE_APP_PASSWORD=$PIHOLE_APP_PASSWORD|" "$SERVICE_FILE"
    echo "✅ Fixed placeholder in service file"
elif sudo grep -q "Environment=PIHOLE_APP_PASSWORD=" "$SERVICE_FILE"; then
    sudo sed -i "s|Environment=PIHOLE_APP_PASSWORD=.*|Environment=PIHOLE_APP_PASSWORD=$PIHOLE_APP_PASSWORD|" "$SERVICE_FILE"
    echo "✅ Updated existing password in service file"
else
    # Add the environment variable after [Service]
    sudo sed -i '/^\[Service\]/a Environment=PIHOLE_APP_PASSWORD='"$PIHOLE_APP_PASSWORD" "$SERVICE_FILE"
    echo "✅ Added password to service file"
fi

# Reload and start
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "🚀 Starting service..."
if sudo systemctl start pihole-stats.service; then
    sleep 3
    if systemctl is-active --quiet pihole-stats.service; then
        echo "✅ Service is running!"
        echo ""
        echo "📊 Status:"
        sudo systemctl status pihole-stats.service --no-pager -l | head -10
    else
        echo "❌ Service failed to stay running"
        echo "📋 Recent logs:"
        sudo journalctl -u pihole-stats --no-pager -n 10
    fi
else
    echo "❌ Failed to start service"
    sudo journalctl -u pihole-stats --no-pager -n 5
fi

echo ""
echo "✅ Done! Monitor with: sudo journalctl -u pihole-stats -f"
