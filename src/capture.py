#!/usr/bin/env python3
"""HDMI capture module - captures frames from USB capture card."""

import subprocess
import tempfile
import base64
from pathlib import Path

DEFAULT_DEVICE = "/dev/video0"
DEFAULT_RESOLUTION = "1920x1080"

def capture_frame(device: str = DEFAULT_DEVICE, 
                  resolution: str = DEFAULT_RESOLUTION,
                  output_path: str = None) -> str:
    """
    Capture a single frame from the HDMI capture device.
    
    Args:
        device: V4L2 device path
        resolution: Video resolution
        output_path: Where to save the image (optional, uses temp file if None)
    
    Returns:
        Path to the captured image
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix='.jpg')
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'v4l2',
        '-video_size', resolution,
        '-i', device,
        '-vframes', '1',
        '-q:v', '2',
        '-update', '1',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if not Path(output_path).exists():
        raise RuntimeError(f"Failed to capture frame: {result.stderr}")
    
    return output_path

def capture_frame_base64(device: str = DEFAULT_DEVICE,
                         resolution: str = DEFAULT_RESOLUTION) -> str:
    """Capture a frame and return as base64-encoded string."""
    path = capture_frame(device, resolution)
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    Path(path).unlink()  # Clean up temp file
    return data

if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "capture.jpg"
    path = capture_frame(output_path=output)
    print(f"Captured: {path}")
