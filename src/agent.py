#!/usr/bin/env python3
"""
RAM KVM AI Agent - Visual feedback control loop.

The agent controls a computer like a human would:
1. Look at the screen (capture)
2. Find the cursor and target
3. Move towards target
4. Check if arrived
5. Click/type when ready
"""

import os
import sys
import json
import time
import base64
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from capture import capture_frame, capture_frame_base64
from hid import Keyboard, Mouse, MOD_CTRL, MOD_META

@dataclass
class Point:
    x: int
    y: int
    
    def distance_to(self, other: 'Point') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    
    def direction_to(self, other: 'Point') -> Tuple[int, int]:
        """Returns normalized direction vector (-1, 0, or 1 for each axis)."""
        dx = other.x - self.x
        dy = other.y - self.y
        return (
            1 if dx > 10 else (-1 if dx < -10 else 0),
            1 if dy > 10 else (-1 if dy < -10 else 0)
        )

@dataclass 
class ScreenAnalysis:
    """Result of analyzing a screen capture."""
    cursor_position: Optional[Point]  # Where the cursor is now
    target_position: Optional[Point]  # Where we want to click
    target_found: bool
    target_description: str
    suggested_action: str  # 'move', 'click', 'type', 'scroll', 'done'
    text_to_type: Optional[str] = None
    confidence: float = 0.0
    raw_response: str = ""

class VisionProvider:
    """Base class for vision model providers."""
    
    def analyze(self, image_base64: str, task: str, context: str = "") -> ScreenAnalysis:
        raise NotImplementedError

class ClaudeVision(VisionProvider):
    """Claude API for vision analysis."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
    
    def analyze(self, image_base64: str, task: str, context: str = "") -> ScreenAnalysis:
        import anthropic
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
        prompt = f"""You are controlling a computer via mouse and keyboard. Analyze this screenshot.

TASK: {task}

CONTEXT: {context}

Analyze the screen and respond with JSON:
{{
    "cursor_position": {{"x": <int or null>, "y": <int or null>}},
    "target_position": {{"x": <int or null>, "y": <int or null>}},
    "target_found": <bool>,
    "target_description": "<what you're looking for>",
    "suggested_action": "<move|click|type|scroll_up|scroll_down|done|error>",
    "text_to_type": "<text if action is type, else null>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}}

Guidelines:
- If cursor is not visible, set cursor_position to null
- target_position should be the CENTER of the element to click
- Use 'move' if cursor needs to move toward target
- Use 'click' only when cursor is very close to target (within ~20px)
- Use 'type' when a text field is focused and ready for input
- Use 'done' when the task appears complete
- Coordinates are in pixels from top-left (0,0)
- Screen resolution is approximately 1920x1080

Respond ONLY with valid JSON, no other text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        raw = response.content[0].text
        
        try:
            # Try to extract JSON from response
            json_str = raw
            if '```' in raw:
                json_str = raw.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
            
            data = json.loads(json_str.strip())
            
            cursor_pos = None
            if data.get('cursor_position') and data['cursor_position'].get('x') is not None:
                cursor_pos = Point(data['cursor_position']['x'], data['cursor_position']['y'])
            
            target_pos = None
            if data.get('target_position') and data['target_position'].get('x') is not None:
                target_pos = Point(data['target_position']['x'], data['target_position']['y'])
            
            return ScreenAnalysis(
                cursor_position=cursor_pos,
                target_position=target_pos,
                target_found=data.get('target_found', False),
                target_description=data.get('target_description', ''),
                suggested_action=data.get('suggested_action', 'error'),
                text_to_type=data.get('text_to_type'),
                confidence=data.get('confidence', 0.0),
                raw_response=raw
            )
        except Exception as e:
            return ScreenAnalysis(
                cursor_position=None,
                target_position=None,
                target_found=False,
                target_description=f"Parse error: {e}",
                suggested_action='error',
                confidence=0.0,
                raw_response=raw
            )

class Agent:
    """
    Main agent class that executes tasks using visual feedback.
    """
    
    def __init__(self, 
                 vision: VisionProvider,
                 keyboard: Keyboard = None,
                 mouse: Mouse = None,
                 capture_device: str = "/dev/video0",
                 screen_resolution: Tuple[int, int] = (1920, 1080),
                 move_speed: int = 40,
                 capture_delay: float = 0.3,
                 max_iterations: int = 50):
        
        self.vision = vision
        self.keyboard = keyboard or Keyboard()
        self.mouse = mouse or Mouse()
        self.capture_device = capture_device
        self.screen_width, self.screen_height = screen_resolution
        self.move_speed = move_speed
        self.capture_delay = capture_delay
        self.max_iterations = max_iterations
        
        # State tracking
        self.iteration = 0
        self.history: List[ScreenAnalysis] = []
        self.estimated_cursor: Optional[Point] = None
    
    def capture(self) -> str:
        """Capture screen and return base64 image."""
        return capture_frame_base64(self.capture_device)
    
    def move_cursor_toward(self, target: Point, speed: int = None) -> None:
        """Move cursor toward target position."""
        speed = speed or self.move_speed
        
        if self.estimated_cursor:
            dx = target.x - self.estimated_cursor.x
            dy = target.y - self.estimated_cursor.y
            
            # Proportional movement (faster when far, slower when close)
            distance = (dx**2 + dy**2) ** 0.5
            if distance < 50:
                speed = max(5, speed // 4)
            elif distance < 150:
                speed = max(10, speed // 2)
            
            # Normalize and scale
            if distance > 0:
                move_x = int((dx / distance) * speed)
                move_y = int((dy / distance) * speed)
            else:
                move_x, move_y = 0, 0
        else:
            # No cursor position known, move toward target from center
            center = Point(self.screen_width // 2, self.screen_height // 2)
            dx = target.x - center.x
            dy = target.y - center.y
            distance = (dx**2 + dy**2) ** 0.5
            if distance > 0:
                move_x = int((dx / distance) * speed)
                move_y = int((dy / distance) * speed)
            else:
                move_x, move_y = 0, 0
        
        self.mouse.move(move_x, move_y)
        
        # Update estimated position
        if self.estimated_cursor:
            self.estimated_cursor = Point(
                self.estimated_cursor.x + move_x,
                self.estimated_cursor.y + move_y
            )
    
    def click(self, button: str = 'left') -> None:
        """Click mouse button."""
        self.mouse.click(button)
    
    def type_text(self, text: str) -> None:
        """Type text via keyboard."""
        self.keyboard.type_string(text)
    
    def press_enter(self) -> None:
        """Press Enter key."""
        self.keyboard.press_special('enter')
    
    def execute_task(self, task: str, callback=None) -> Dict[str, Any]:
        """
        Execute a task using visual feedback loop.
        
        Args:
            task: Natural language description of what to do
            callback: Optional function called after each iteration with 
                     (iteration, analysis, action_taken) args
        
        Returns:
            Dict with 'success', 'iterations', 'history', 'error' keys
        """
        self.iteration = 0
        self.history = []
        context = ""
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            
            # 1. Capture screen
            try:
                image_b64 = self.capture()
            except Exception as e:
                return {
                    'success': False,
                    'iterations': self.iteration,
                    'history': self.history,
                    'error': f"Capture failed: {e}"
                }
            
            time.sleep(self.capture_delay)
            
            # 2. Analyze with vision
            try:
                analysis = self.vision.analyze(image_b64, task, context)
                self.history.append(analysis)
            except Exception as e:
                return {
                    'success': False,
                    'iterations': self.iteration,
                    'history': self.history,
                    'error': f"Vision failed: {e}"
                }
            
            # Update cursor estimate if vision found it
            if analysis.cursor_position:
                self.estimated_cursor = analysis.cursor_position
            
            action_taken = analysis.suggested_action
            
            # 3. Execute suggested action
            if analysis.suggested_action == 'done':
                if callback:
                    callback(self.iteration, analysis, 'done')
                return {
                    'success': True,
                    'iterations': self.iteration,
                    'history': self.history,
                    'error': None
                }
            
            elif analysis.suggested_action == 'error':
                context += f"\nIteration {self.iteration}: Error - {analysis.target_description}"
                if callback:
                    callback(self.iteration, analysis, 'error')
                continue
            
            elif analysis.suggested_action == 'move':
                if analysis.target_position:
                    self.move_cursor_toward(analysis.target_position)
                    context += f"\nIteration {self.iteration}: Moved toward {analysis.target_description}"
                if callback:
                    callback(self.iteration, analysis, 'move')
            
            elif analysis.suggested_action == 'click':
                self.click()
                context += f"\nIteration {self.iteration}: Clicked on {analysis.target_description}"
                if callback:
                    callback(self.iteration, analysis, 'click')
                time.sleep(0.5)  # Wait for UI response
            
            elif analysis.suggested_action == 'type':
                if analysis.text_to_type:
                    self.type_text(analysis.text_to_type)
                    context += f"\nIteration {self.iteration}: Typed '{analysis.text_to_type}'"
                if callback:
                    callback(self.iteration, analysis, 'type')
            
            elif analysis.suggested_action == 'scroll_up':
                # Implement scroll via mouse wheel or keyboard
                self.keyboard.press_special('pageup')
                context += f"\nIteration {self.iteration}: Scrolled up"
                if callback:
                    callback(self.iteration, analysis, 'scroll_up')
            
            elif analysis.suggested_action == 'scroll_down':
                self.keyboard.press_special('pagedown')
                context += f"\nIteration {self.iteration}: Scrolled down"
                if callback:
                    callback(self.iteration, analysis, 'scroll_down')
        
        return {
            'success': False,
            'iterations': self.iteration,
            'history': self.history,
            'error': "Max iterations reached"
        }

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='RAM KVM AI Agent')
    parser.add_argument('task', help='Task to execute')
    parser.add_argument('--device', default='/dev/video0', help='Capture device')
    parser.add_argument('--dry-run', action='store_true', help='Analyze only, no HID actions')
    parser.add_argument('--max-iter', type=int, default=50, help='Max iterations')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup vision provider
    vision = ClaudeVision()
    
    # Setup agent
    if args.dry_run:
        # Mock HID for dry run
        class MockHID:
            def move(self, x, y): pass
            def click(self, btn='left'): pass
            def type_string(self, s): pass
            def press_special(self, k): pass
        
        agent = Agent(
            vision=vision,
            keyboard=MockHID(),
            mouse=MockHID(),
            capture_device=args.device,
            max_iterations=args.max_iter
        )
    else:
        agent = Agent(
            vision=vision,
            capture_device=args.device,
            max_iterations=args.max_iter
        )
    
    def on_iteration(i, analysis, action):
        if args.verbose:
            print(f"\n[{i}] Action: {action}")
            print(f"    Target: {analysis.target_description}")
            print(f"    Confidence: {analysis.confidence:.2f}")
            if analysis.cursor_position:
                print(f"    Cursor: ({analysis.cursor_position.x}, {analysis.cursor_position.y})")
            if analysis.target_position:
                print(f"    Target pos: ({analysis.target_position.x}, {analysis.target_position.y})")
    
    print(f"Executing task: {args.task}")
    print("-" * 50)
    
    result = agent.execute_task(args.task, callback=on_iteration if args.verbose else None)
    
    print("-" * 50)
    if result['success']:
        print(f"✅ Task completed in {result['iterations']} iterations")
    else:
        print(f"❌ Task failed: {result['error']}")
        print(f"   Iterations: {result['iterations']}")

if __name__ == "__main__":
    main()
