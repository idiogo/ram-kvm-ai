#!/usr/bin/env python3
"""
RAM KVM AI Viewer - Real-time visualization of agent's vision.

Shows what the agent is seeing and its decision-making process.
"""

import cv2
import numpy as np
import threading
import queue
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

@dataclass
class ViewerFrame:
    """A frame to display in the viewer."""
    image: np.ndarray  # BGR image
    iteration: int
    action: str
    target_description: str
    cursor_pos: Optional[Tuple[int, int]] = None
    target_pos: Optional[Tuple[int, int]] = None
    confidence: float = 0.0

class Viewer:
    """
    Real-time viewer for agent's vision.
    
    Opens a window showing:
    - Current screen capture
    - Cursor position (if detected)
    - Target position (if detected)
    - Current action and iteration
    """
    
    def __init__(self, 
                 window_name: str = "RAM KVM AI - Vision",
                 window_width: int = 960,
                 window_height: int = 540,
                 show_overlay: bool = True):
        
        self.window_name = window_name
        self.window_width = window_width
        self.window_height = window_height
        self.show_overlay = show_overlay
        
        self._running = False
        self._frame_queue = queue.Queue(maxsize=5)
        self._thread: Optional[threading.Thread] = None
        self._current_frame: Optional[ViewerFrame] = None
        
        # Colors (BGR)
        self.COLOR_CURSOR = (0, 255, 0)    # Green
        self.COLOR_TARGET = (0, 0, 255)    # Red
        self.COLOR_LINE = (255, 255, 0)    # Cyan
        self.COLOR_TEXT_BG = (0, 0, 0)     # Black
        self.COLOR_TEXT = (255, 255, 255)  # White
    
    def start(self):
        """Start the viewer in a separate thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the viewer."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        cv2.destroyAllWindows()
    
    def update(self, frame: ViewerFrame):
        """Update the displayed frame (non-blocking)."""
        try:
            # Clear old frames if queue is full
            while self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break
            self._frame_queue.put_nowait(frame)
        except queue.Full:
            pass  # Skip frame if queue is full
    
    def update_from_capture(self, 
                            image_path: str,
                            iteration: int = 0,
                            action: str = "",
                            target_description: str = "",
                            cursor_pos: Optional[Tuple[int, int]] = None,
                            target_pos: Optional[Tuple[int, int]] = None,
                            confidence: float = 0.0):
        """Update from a captured image file."""
        img = cv2.imread(image_path)
        if img is None:
            return
        
        frame = ViewerFrame(
            image=img,
            iteration=iteration,
            action=action,
            target_description=target_description,
            cursor_pos=cursor_pos,
            target_pos=target_pos,
            confidence=confidence
        )
        self.update(frame)
    
    def update_from_base64(self,
                           image_b64: str,
                           iteration: int = 0,
                           action: str = "",
                           target_description: str = "",
                           cursor_pos: Optional[Tuple[int, int]] = None,
                           target_pos: Optional[Tuple[int, int]] = None,
                           confidence: float = 0.0):
        """Update from a base64-encoded image."""
        import base64
        
        img_bytes = base64.b64decode(image_b64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return
        
        frame = ViewerFrame(
            image=img,
            iteration=iteration,
            action=action,
            target_description=target_description,
            cursor_pos=cursor_pos,
            target_pos=target_pos,
            confidence=confidence
        )
        self.update(frame)
    
    def _draw_overlay(self, img: np.ndarray, frame: ViewerFrame) -> np.ndarray:
        """Draw overlay information on the image."""
        h, w = img.shape[:2]
        
        # Scale positions to resized image
        scale_x = w / 1920  # Assuming 1920 original width
        scale_y = h / 1080  # Assuming 1080 original height
        
        # Draw cursor position
        if frame.cursor_pos:
            cx = int(frame.cursor_pos[0] * scale_x)
            cy = int(frame.cursor_pos[1] * scale_y)
            cv2.circle(img, (cx, cy), 15, self.COLOR_CURSOR, 2)
            cv2.circle(img, (cx, cy), 3, self.COLOR_CURSOR, -1)
            cv2.putText(img, "CURSOR", (cx + 20, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_CURSOR, 1)
        
        # Draw target position
        if frame.target_pos:
            tx = int(frame.target_pos[0] * scale_x)
            ty = int(frame.target_pos[1] * scale_y)
            cv2.drawMarker(img, (tx, ty), self.COLOR_TARGET, 
                          cv2.MARKER_CROSS, 30, 2)
            cv2.putText(img, "TARGET", (tx + 20, ty - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_TARGET, 1)
        
        # Draw line from cursor to target
        if frame.cursor_pos and frame.target_pos:
            cx = int(frame.cursor_pos[0] * scale_x)
            cy = int(frame.cursor_pos[1] * scale_y)
            tx = int(frame.target_pos[0] * scale_x)
            ty = int(frame.target_pos[1] * scale_y)
            cv2.line(img, (cx, cy), (tx, ty), self.COLOR_LINE, 1, cv2.LINE_AA)
        
        # Draw info panel at bottom
        panel_height = 80
        cv2.rectangle(img, (0, h - panel_height), (w, h), self.COLOR_TEXT_BG, -1)
        
        # Iteration and action
        text1 = f"Iteration: {frame.iteration} | Action: {frame.action.upper()} | Confidence: {frame.confidence:.0%}"
        cv2.putText(img, text1, (10, h - panel_height + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_TEXT, 1)
        
        # Target description (truncate if too long)
        desc = frame.target_description[:80] + "..." if len(frame.target_description) > 80 else frame.target_description
        cv2.putText(img, f"Target: {desc}", (10, h - panel_height + 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_TEXT, 1)
        
        return img
    
    def _run_loop(self):
        """Main viewer loop (runs in separate thread)."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        
        # Create placeholder image
        placeholder = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        cv2.putText(placeholder, "Waiting for capture...", 
                   (self.window_width // 4, self.window_height // 2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
        
        while self._running:
            # Check for new frame
            try:
                frame = self._frame_queue.get(timeout=0.1)
                self._current_frame = frame
            except queue.Empty:
                pass
            
            # Display current frame
            if self._current_frame:
                img = self._current_frame.image.copy()
                img = cv2.resize(img, (self.window_width, self.window_height))
                
                if self.show_overlay:
                    img = self._draw_overlay(img, self._current_frame)
                
                cv2.imshow(self.window_name, img)
            else:
                cv2.imshow(self.window_name, placeholder)
            
            # Handle key events
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                self._running = False
                break
            elif key == ord('o'):  # Toggle overlay
                self.show_overlay = not self.show_overlay
            elif key == ord('s'):  # Save current frame
                if self._current_frame is not None:
                    filename = f"capture_{int(time.time())}.jpg"
                    cv2.imwrite(filename, self._current_frame.image)
                    print(f"Saved: {filename}")
        
        cv2.destroyAllWindows()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


class ViewerCallback:
    """
    Callback wrapper that updates the viewer on each agent iteration.
    
    Usage:
        viewer = Viewer()
        viewer.start()
        
        callback = ViewerCallback(viewer)
        agent.execute_task("...", callback=callback)
    """
    
    def __init__(self, viewer: Viewer, capture_func=None):
        self.viewer = viewer
        self.capture_func = capture_func
        self._last_image_b64: Optional[str] = None
    
    def set_last_capture(self, image_b64: str):
        """Set the last captured image (called by agent before analysis)."""
        self._last_image_b64 = image_b64
    
    def __call__(self, iteration: int, analysis, action: str):
        """Called by agent after each iteration."""
        if self._last_image_b64:
            cursor = None
            target = None
            
            if analysis.cursor_position:
                cursor = (analysis.cursor_position.x, analysis.cursor_position.y)
            if analysis.target_position:
                target = (analysis.target_position.x, analysis.target_position.y)
            
            self.viewer.update_from_base64(
                self._last_image_b64,
                iteration=iteration,
                action=action,
                target_description=analysis.target_description,
                cursor_pos=cursor,
                target_pos=target,
                confidence=analysis.confidence
            )


def main():
    """Test the viewer with a sample image."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python viewer.py <image_path>")
        print("       python viewer.py --capture  # Live capture test")
        sys.exit(1)
    
    viewer = Viewer()
    viewer.start()
    
    if sys.argv[1] == "--capture":
        # Live capture test
        from capture import capture_frame
        
        iteration = 0
        while True:
            try:
                path = capture_frame(output_path="/tmp/viewer_test.jpg")
                viewer.update_from_capture(
                    path,
                    iteration=iteration,
                    action="capturing",
                    target_description="Live capture test - press 'q' to quit"
                )
                iteration += 1
                time.sleep(0.5)
            except KeyboardInterrupt:
                break
    else:
        # Single image test
        viewer.update_from_capture(
            sys.argv[1],
            iteration=1,
            action="test",
            target_description="Test image - press 'q' to quit",
            cursor_pos=(500, 300),
            target_pos=(800, 500),
            confidence=0.85
        )
        
        # Keep running until user quits
        while viewer._running:
            time.sleep(0.1)
    
    viewer.stop()

if __name__ == "__main__":
    main()
