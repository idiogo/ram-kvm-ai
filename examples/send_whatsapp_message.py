#!/usr/bin/env python3
"""
Example: Send a WhatsApp message using RAM KVM AI.

Usage:
    python examples/send_whatsapp_message.py "João" "Oi, tudo bem?"
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import Agent, ClaudeVision

def main():
    if len(sys.argv) < 3:
        print("Usage: python send_whatsapp_message.py <contact_name> <message>")
        print("Example: python send_whatsapp_message.py 'João' 'Oi!'")
        sys.exit(1)
    
    contact = sys.argv[1]
    message = sys.argv[2]
    
    # Initialize
    vision = ClaudeVision()
    agent = Agent(
        vision=vision,
        capture_device="/dev/video0",
        max_iterations=30
    )
    
    # Compose task
    task = f"""
    Send a WhatsApp message to {contact}.
    
    Steps:
    1. Find and click the search bar at the top
    2. Type "{contact}" to search for the contact
    3. Click on the contact when it appears in results
    4. Click on the message input field at the bottom
    5. Type the message: "{message}"
    6. Press Enter to send
    
    The task is complete when the message appears in the chat.
    """
    
    print(f"🎯 Task: Send '{message}' to {contact}")
    print("-" * 50)
    
    def on_step(i, analysis, action):
        print(f"[{i:2d}] {action:10s} | {analysis.target_description[:50]}")
    
    result = agent.execute_task(task, callback=on_step)
    
    print("-" * 50)
    if result['success']:
        print(f"✅ Message sent in {result['iterations']} steps!")
    else:
        print(f"❌ Failed: {result['error']}")
        print(f"   Steps completed: {result['iterations']}")

if __name__ == "__main__":
    main()
