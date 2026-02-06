#!/bin/bash
# Setup USB HID Gadget for Raspberry Pi
# This script creates keyboard + mouse HID devices
# 
# Prerequisites:
# 1. Add to /boot/firmware/config.txt under [all]:
#    dtoverlay=dwc2,dr_mode=peripheral
#
# 2. Add to /boot/firmware/cmdline.txt (end of line):
#    modules-load=dwc2,libcomposite
#
# 3. Reboot after changes

set -e

GADGET_NAME="ramkvm"
GADGET_PATH="/sys/kernel/config/usb_gadget/${GADGET_NAME}"

# Check if already configured
if [ -d "$GADGET_PATH" ]; then
    echo "Gadget already exists at $GADGET_PATH"
    echo "Current UDC state: $(cat /sys/class/udc/*/state 2>/dev/null || echo 'unknown')"
    exit 0
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Check if configfs is available
if [ ! -d /sys/kernel/config/usb_gadget ]; then
    echo "Error: USB gadget configfs not available"
    echo "Make sure libcomposite module is loaded and dwc2 overlay is enabled"
    exit 1
fi

echo "Creating USB HID gadget..."

# Create gadget
mkdir -p "$GADGET_PATH"
cd "$GADGET_PATH"

# Device identifiers
echo 0x1d6b > idVendor   # Linux Foundation
echo 0x0104 > idProduct  # Multifunction Composite Gadget
echo 0x0100 > bcdDevice  # v1.0.0
echo 0x0200 > bcdUSB     # USB 2.0

# Device strings
mkdir -p strings/0x409
echo "ramkvm001" > strings/0x409/serialnumber
echo "RAM KVM AI" > strings/0x409/manufacturer
echo "RAM KVM HID Device" > strings/0x409/product

# Configuration
mkdir -p configs/c.1/strings/0x409
echo "HID Keyboard + Mouse" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower  # 250mA

# === KEYBOARD HID ===
mkdir -p functions/hid.keyboard
echo 1 > functions/hid.keyboard/protocol      # Keyboard protocol
echo 1 > functions/hid.keyboard/subclass      # Boot interface subclass
echo 8 > functions/hid.keyboard/report_length # 8-byte reports

# Keyboard HID Report Descriptor
# Standard boot keyboard: modifier, reserved, 6 keycodes
echo -ne '\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0' > functions/hid.keyboard/report_desc

# === MOUSE HID ===
mkdir -p functions/hid.mouse
echo 2 > functions/hid.mouse/protocol      # Mouse protocol
echo 1 > functions/hid.mouse/subclass      # Boot interface subclass
echo 3 > functions/hid.mouse/report_length # 3-byte reports (buttons, x, y)

# Mouse HID Report Descriptor
# Simple relative mouse: buttons (3), X, Y
echo -ne '\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x15\x81\x25\x7f\x75\x08\x95\x02\x81\x06\xc0\xc0' > functions/hid.mouse/report_desc

# Link functions to configuration
ln -sf functions/hid.keyboard configs/c.1/
ln -sf functions/hid.mouse configs/c.1/

# Enable gadget by binding to UDC
UDC=$(ls /sys/class/udc | head -1)
if [ -z "$UDC" ]; then
    echo "Error: No UDC found. Is dwc2 overlay enabled?"
    exit 1
fi

echo "$UDC" > UDC

echo "✅ USB HID Gadget created!"
echo "   Keyboard: /dev/hidg0"
echo "   Mouse:    /dev/hidg1"
echo "   UDC:      $UDC"

# Set permissions
sleep 1
chmod 666 /dev/hidg0 /dev/hidg1 2>/dev/null || true

echo ""
echo "UDC state: $(cat /sys/class/udc/*/state)"
