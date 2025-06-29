"""Calendar styling and visual constants."""

from typing import Dict
from PIL import ImageFont

# Layout constants
HEADER_HEIGHT: int = 80  # Keep as before
TASK_HEIGHT: int = 40    # Keep as before
PADDING: int = 8         # Keep as before
TASK_PADDING: int = 4    # Keep as before
CALENDAR_WIDTH_RATIO: float = 0.85  # 85% of display width
LINE_HEIGHT: int = 24    # Keep as before

# Font sizes
DEFAULT_FONT_SIZE: int = 14      # Doubled from 28
DEFAULT_TASK_FONT_SIZE: int = 12 # Doubled from 24
TIMESTAMP_FONT_SIZE: int = 10    # Doubled from 20

# Text length limits
MAX_TITLE_LENGTH: int = 25       # Increased from 25
MAX_TIMED_TITLE_LENGTH: int = 20 # Increased from 20 

FONT_PATH = ImageFont.truetype("DejaVuSans.ttf", size=10).path
