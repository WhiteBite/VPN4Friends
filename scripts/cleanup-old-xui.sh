#!/bin/bash
# Script to remove old x-ui installation (non-Docker)

echo "=== Cleaning up old x-ui installation ==="

# Stop and disable service
if systemctl is-active --quiet x-ui; then
    echo "Stopping x-ui service..."
    systemctl stop x-ui
fi

if systemctl is-enabled --quiet x-ui 2>/dev/null; then
    echo "Disabling x-ui service..."
    systemctl disable x-ui
fi

# Remove service file
if [ -f /etc/systemd/system/x-ui.service ]; then
    echo "Removing service file..."
    rm -f /etc/systemd/system/x-ui.service
    systemctl daemon-reload
fi

# Remove installation directory
if [ -d /usr/local/x-ui ]; then
    echo "Removing /usr/local/x-ui..."
    rm -rf /usr/local/x-ui
fi

# Check for any remaining processes
OLD_PROCESSES=$(ps aux | grep -E "/usr/local/x-ui|x-ui" | grep -v grep | grep -v docker | awk '{print $2}')
if [ -n "$OLD_PROCESSES" ]; then
    echo "Killing remaining processes: $OLD_PROCESSES"
    kill -9 $OLD_PROCESSES 2>/dev/null
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Verification:"
systemctl status x-ui --no-pager 2>&1 | head -3 || echo "  ✅ Service not found"
ls -la /usr/local/ | grep x-ui && echo "  ❌ Files still exist" || echo "  ✅ Files removed"
ps aux | grep x-ui | grep -v grep | grep -v docker && echo "  ❌ Processes still running" || echo "  ✅ No old processes"
