#!/usr/bin/env python3
"""
Example: Run agent with real-time viewer on Pi display.

The viewer window shows:
- Current screen capture
- Cursor position (green circle)
- Target position (red cross)
- Line connecting cursor to target
- Current action and iteration info

Keyboard shortcuts in viewer:
- Q or ESC: Quit
- O: Toggle overlay
- S: Save current frame
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import Agent, ClaudeVision
from viewer import Viewer

def main():
    if len(sys.argv) < 2:
        print("Usage: python with_viewer.py <task>")
        print("Example: python with_viewer.py 'Click on Chrome icon'")
        sys.exit(1)
    
    task = sys.argv[1]
    
    # Create and start viewer
    print("🖥️  Starting viewer window...")
    viewer = Viewer(
        window_name="RAM KVM AI - Vision",
        window_width=960,
        window_height=540,
        show_overlay=True
    )
    viewer.start()
    
    # Create agent with viewer
    print("🤖 Initializing agent...")
    vision = ClaudeVision()
    agent = Agent(
        vision=vision,
        capture_device="/dev/video0",
        max_iterations=30,
        viewer=viewer  # Pass viewer to agent
    )
    
    print(f"🎯 Task: {task}")
    print("-" * 50)
    print("Watch the viewer window to see what I'm seeing!")
    print("-" * 50)
    
    def on_step(i, analysis, action):
        status = "✅" if action == "done" else "🔄"
        print(f"{status} [{i:2d}] {action:10s} | {analysis.target_description[:50]}")
    
    try:
        result = agent.execute_task(task, callback=on_step)
        
        print("-" * 50)
        if result['success']:
            print(f"✅ Task completed in {result['iterations']} steps!")
        else:
            print(f"❌ Failed: {result['error']}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    
    finally:
        print("Closing viewer...")
        viewer.stop()

if __name__ == "__main__":
    main()
