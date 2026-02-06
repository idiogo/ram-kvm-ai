#!/bin/bash
# Remove USB HID Gadget

set -e

GADGET_NAME="ramkvm"
GADGET_PATH="/sys/kernel/config/usb_gadget/${GADGET_NAME}"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

if [ ! -d "$GADGET_PATH" ]; then
    echo "Gadget not found at $GADGET_PATH"
    exit 0
fi

cd "$GADGET_PATH"

# Disable gadget
echo "" > UDC 2>/dev/null || true

# Remove symlinks
rm -f configs/c.1/hid.keyboard 2>/dev/null || true
rm -f configs/c.1/hid.mouse 2>/dev/null || true

# Remove strings and configs
rmdir configs/c.1/strings/0x409 2>/dev/null || true
rmdir configs/c.1 2>/dev/null || true
rmdir strings/0x409 2>/dev/null || true

# Remove functions
rmdir functions/hid.keyboard 2>/dev/null || true
rmdir functions/hid.mouse 2>/dev/null || true

# Remove gadget
cd /
rmdir "$GADGET_PATH" 2>/dev/null || true

echo "✅ USB HID Gadget removed"
