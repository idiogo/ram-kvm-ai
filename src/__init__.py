"""RAM KVM AI - Autonomous computer control via visual feedback."""

from .agent import Agent, ClaudeVision, ScreenAnalysis, Point
from .capture import capture_frame, capture_frame_base64
from .hid import Keyboard, Mouse, MOD_CTRL, MOD_SHIFT, MOD_ALT, MOD_META
from .viewer import Viewer, ViewerCallback, ViewerFrame

__version__ = "0.1.0"
__all__ = [
    'Agent', 'ClaudeVision', 'ScreenAnalysis', 'Point',
    'capture_frame', 'capture_frame_base64',
    'Keyboard', 'Mouse',
    'MOD_CTRL', 'MOD_SHIFT', 'MOD_ALT', 'MOD_META',
    'Viewer', 'ViewerCallback', 'ViewerFrame',
]
