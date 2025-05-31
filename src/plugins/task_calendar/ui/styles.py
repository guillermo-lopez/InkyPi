"""Calendar styling and visual constants."""

from typing import Dict

# Priority colors for tasks
PRIORITY_COLORS: Dict[int, str] = {
    0: 'blue',   # Normal
    1: 'black',    # Low
    2: 'orange',  # Medium
    3: 'pink'     # High
}

# Event source colors
EVENT_COLORS: Dict[str, str] = {
    'google': 'red',  # Google Calendar events
    'ticktick': '#FF5722'  # TickTick orange
}

# Layout constants
HEADER_HEIGHT: int = 60
TASK_HEIGHT: int = 30
PADDING: int = 5
TASK_PADDING: int = 2
CALENDAR_WIDTH_RATIO: float = 0.85  # 85% of display width

# Font sizes
DEFAULT_FONT_SIZE: int = 20
DEFAULT_TASK_FONT_SIZE: int = 16
TIMESTAMP_FONT_SIZE: int = 14

# Text length limits
MAX_TITLE_LENGTH: int = 25
MAX_TIMED_TITLE_LENGTH: int = 20 
