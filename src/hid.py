#!/usr/bin/env python3
"""USB HID gadget module - keyboard and mouse control."""

import struct
import time
from pathlib import Path

KEYBOARD_DEV = "/dev/hidg0"
MOUSE_DEV = "/dev/hidg1"

# HID keyboard scan codes (US layout)
KEYMAP = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D, '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21,
    '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    ' ': 0x2C, '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31,
    ';': 0x33, "'": 0x34, '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
    '\n': 0x28, '\t': 0x2B, '\b': 0x2A,
}

SHIFT_CHARS = {
    'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'E': 'e', 'F': 'f', 'G': 'g',
    'H': 'h', 'I': 'i', 'J': 'j', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n',
    'O': 'o', 'P': 'p', 'Q': 'q', 'R': 'r', 'S': 's', 'T': 't', 'U': 'u',
    'V': 'v', 'W': 'w', 'X': 'x', 'Y': 'y', 'Z': 'z',
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7',
    '*': '8', '(': '9', ')': '0', '_': '-', '+': '=', '{': '[', '}': ']',
    '|': '\\', ':': ';', '"': "'", '~': '`', '<': ',', '>': '.', '?': '/',
}

# Special keys
SPECIAL_KEYS = {
    'enter': 0x28, 'escape': 0x29, 'backspace': 0x2A, 'tab': 0x2B,
    'space': 0x2C, 'capslock': 0x39, 'f1': 0x3A, 'f2': 0x3B, 'f3': 0x3C,
    'f4': 0x3D, 'f5': 0x3E, 'f6': 0x3F, 'f7': 0x40, 'f8': 0x41, 'f9': 0x42,
    'f10': 0x43, 'f11': 0x44, 'f12': 0x45, 'right': 0x4F, 'left': 0x50,
    'down': 0x51, 'up': 0x52, 'delete': 0x4C, 'home': 0x4A, 'end': 0x4D,
    'pageup': 0x4B, 'pagedown': 0x4E,
}

# Modifier keys
MOD_NONE = 0x00
MOD_CTRL = 0x01
MOD_SHIFT = 0x02
MOD_ALT = 0x04
MOD_META = 0x08  # Cmd on Mac, Win on Windows

class Keyboard:
    def __init__(self, device: str = KEYBOARD_DEV):
        self.device = device
    
    def _send_report(self, modifier: int, keycode: int):
        """Send a keyboard HID report."""
        report = bytes([modifier, 0, keycode, 0, 0, 0, 0, 0])
        with open(self.device, 'wb') as f:
            f.write(report)
    
    def press_key(self, char: str, modifier: int = MOD_NONE):
        """Press and release a single key."""
        if char in SHIFT_CHARS:
            modifier |= MOD_SHIFT
            char = SHIFT_CHARS[char]
        
        keycode = KEYMAP.get(char, 0)
        if keycode == 0:
            return
        
        self._send_report(modifier, keycode)
        time.sleep(0.02)
        self._send_report(0, 0)  # Release
        time.sleep(0.02)
    
    def press_special(self, key: str, modifier: int = MOD_NONE):
        """Press a special key (enter, escape, arrow keys, etc)."""
        keycode = SPECIAL_KEYS.get(key.lower(), 0)
        if keycode == 0:
            return
        
        self._send_report(modifier, keycode)
        time.sleep(0.02)
        self._send_report(0, 0)
        time.sleep(0.02)
    
    def type_string(self, text: str, delay: float = 0.02):
        """Type a string character by character."""
        for char in text:
            self.press_key(char)
            time.sleep(delay)
    
    def hotkey(self, *keys):
        """Press a key combination (e.g., hotkey('ctrl', 'c'))."""
        modifier = MOD_NONE
        keycode = 0
        
        for key in keys:
            key = key.lower()
            if key in ('ctrl', 'control'):
                modifier |= MOD_CTRL
            elif key in ('shift',):
                modifier |= MOD_SHIFT
            elif key in ('alt', 'option'):
                modifier |= MOD_ALT
            elif key in ('meta', 'cmd', 'command', 'win', 'super'):
                modifier |= MOD_META
            elif key in SPECIAL_KEYS:
                keycode = SPECIAL_KEYS[key]
            elif len(key) == 1 and key in KEYMAP:
                keycode = KEYMAP[key]
        
        self._send_report(modifier, keycode)
        time.sleep(0.05)
        self._send_report(0, 0)
        time.sleep(0.02)

class Mouse:
    def __init__(self, device: str = MOUSE_DEV):
        self.device = device
    
    def _send_report(self, buttons: int, x: int, y: int):
        """Send a mouse HID report."""
        x = max(-127, min(127, x))
        y = max(-127, min(127, y))
        report = struct.pack('bbb', buttons, x, y)
        with open(self.device, 'wb') as f:
            f.write(report)
    
    def move(self, x: int, y: int):
        """Move mouse by relative offset."""
        self._send_report(0, x, y)
        time.sleep(0.01)
    
    def click(self, button: str = 'left'):
        """Click a mouse button."""
        btn = {'left': 1, 'right': 2, 'middle': 4}.get(button, 1)
        self._send_report(btn, 0, 0)
        time.sleep(0.05)
        self._send_report(0, 0, 0)
        time.sleep(0.02)
    
    def move_to(self, target_x: int, target_y: int, 
                screen_width: int = 1920, screen_height: int = 1080,
                current_x: int = None, current_y: int = None):
        """
        Move mouse to absolute position.
        Note: HID mouse is relative, so we need to know current position
        or move from a known position (like corner).
        """
        # Move to corner first if position unknown
        if current_x is None or current_y is None:
            # Move to top-left corner (overshoot to ensure we're there)
            for _ in range(20):
                self.move(-127, -127)
            current_x, current_y = 0, 0
        
        # Calculate delta
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Move in steps
        while abs(dx) > 0 or abs(dy) > 0:
            step_x = max(-127, min(127, dx))
            step_y = max(-127, min(127, dy))
            self.move(step_x, step_y)
            dx -= step_x
            dy -= step_y

if __name__ == "__main__":
    print("Testing keyboard...")
    kb = Keyboard()
    kb.type_string("Hello from PiKVM Agent!")
    kb.press_special('enter')
