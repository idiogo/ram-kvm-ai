#!/usr/bin/env python3
"""
Simple test: Capture screen and analyze without taking action.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from capture import capture_frame_base64
from agent import ClaudeVision

def main():
    print("📸 Capturing screen...")
    image_b64 = capture_frame_base64("/dev/video0")
    print(f"   Captured {len(image_b64)} bytes (base64)")
    
    print("\n🔍 Analyzing with Claude Vision...")
    vision = ClaudeVision()
    
    analysis = vision.analyze(
        image_b64,
        task="Describe what you see on this screen. Where is the cursor?",
        context=""
    )
    
    print(f"\n📊 Analysis:")
    print(f"   Cursor: {analysis.cursor_position}")
    print(f"   Target found: {analysis.target_found}")
    print(f"   Description: {analysis.target_description}")
    print(f"   Suggested action: {analysis.suggested_action}")
    print(f"   Confidence: {analysis.confidence:.2f}")
    print(f"\n📝 Raw response:\n{analysis.raw_response}")

if __name__ == "__main__":
    main()
