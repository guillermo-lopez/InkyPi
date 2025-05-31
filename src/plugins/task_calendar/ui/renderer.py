"""Calendar rendering and drawing functionality."""

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

from .styles import (
    PRIORITY_COLORS, EVENT_COLORS, HEADER_HEIGHT, TASK_HEIGHT,
    PADDING, TASK_PADDING, DEFAULT_FONT_SIZE, DEFAULT_TASK_FONT_SIZE,
    TIMESTAMP_FONT_SIZE, MAX_TITLE_LENGTH, MAX_TIMED_TITLE_LENGTH
)
from .layout import calculate_week_start, calculate_day_index, calculate_item_height

logger = logging.getLogger(__name__)

class CalendarRenderer:
    """Handles the rendering of calendar elements."""

    def __init__(self):
        """Initialize the calendar renderer."""
        self.header_font = None
        self.task_font = None
        self.timestamp_font = None
        self._load_fonts()

    def _load_fonts(self) -> None:
        """Load fonts for calendar display with fallback to default."""
        try:
            self.header_font = ImageFont.truetype("arial.ttf", DEFAULT_FONT_SIZE)
            self.task_font = ImageFont.truetype("arial.ttf", DEFAULT_TASK_FONT_SIZE)
            self.timestamp_font = ImageFont.truetype("arial.ttf", TIMESTAMP_FONT_SIZE)
        except Exception as e:
            logger.warning(f"Failed to load custom fonts: {e}. Using default fonts.")
            self.header_font = None
            self.task_font = None
            self.timestamp_font = None

    def draw_calendar_structure(self, draw: ImageDraw.Draw, x_offset: int, day_width: int, 
                              height: int) -> None:
        """Draw the basic calendar structure including headers and grid lines."""
        today = datetime.now()
        week_start = calculate_week_start()

        # Draw day headers
        for i in range(7):
            x = x_offset + i * day_width
            date = week_start + timedelta(days=i)
            day_name = date.strftime('%a')
            day_num = date.strftime('%d')
            
            # Use yellow background for current day
            is_today = date.date() == today.date()
            header_color = '#ffff00' if is_today else '#f7f7f7'
            
            draw.rectangle([x, 0, x + day_width, HEADER_HEIGHT], 
                         outline='black', fill=header_color)
            draw.text((x + PADDING, PADDING), day_name, 
                     fill='black', font=self.header_font)
            draw.text((x + PADDING, PADDING + 25), day_num, 
                     fill='black', font=self.header_font)

        # Draw vertical grid lines
        for i in range(8):
            x = x_offset + i * day_width
            draw.line([x, HEADER_HEIGHT, x, height], 
                     fill='#cccccc', width=1)

    def draw_calendar_items(self, draw: ImageDraw.Draw, items: List[Dict[str, Any]], 
                          x_offset: int, day_width: int) -> None:
        """Draw tasks and events on the calendar."""
        week_start = calculate_week_start()

        # Organize items by day
        items_by_day: List[List[Dict[str, Any]]] = [[] for _ in range(7)]
        for item in items:
            day_idx = calculate_day_index(item['start'], week_start)
            if 0 <= day_idx < 7:
                items_by_day[day_idx].append(item)

        # Sort and draw items for each day
        for day_idx, day_items in enumerate(items_by_day):
            day_items.sort(key=lambda x: x['start'])
            self.draw_day_items(draw, day_idx, day_items, x_offset, day_width)

    def draw_day_items(self, draw: ImageDraw.Draw, day_idx: int, day_items: List[Dict[str, Any]], 
                      x_offset: int, day_width: int) -> None:
        """Draw items for a specific day."""
        x = x_offset + day_idx * day_width
        y = HEADER_HEIGHT + PADDING

        # Draw all-day items first
        all_day_items = [i for i in day_items if i['is_all_day']]
        for item in all_day_items:
            color = self.get_item_color(item)
            self.draw_item(draw, item, x, y, day_width, color)
            y += TASK_HEIGHT + PADDING

        # Draw timed items
        timed_items = [i for i in day_items if not i['is_all_day']]
        for item in timed_items:
            color = self.get_item_color(item)
            time_str = item['start'].strftime('%-I:%M %p')
            title = f"{time_str} {item['title'][:MAX_TIMED_TITLE_LENGTH]}"
            item_height = calculate_item_height(item, TASK_HEIGHT)
            self.draw_item(draw, item, x, y, day_width, color, title, item_height)
            y += item_height + PADDING

    def draw_item(self, draw: ImageDraw.Draw, item: Dict[str, Any], x: int, y: int, 
                 day_width: int, color: str, title: Optional[str] = None, 
                 height: Optional[int] = None) -> None:
        """Draw a single calendar item."""
        if title is None:
            title = item['title'][:MAX_TITLE_LENGTH]
            
        if height is None:
            height = TASK_HEIGHT
            
        draw.rectangle([x + TASK_PADDING, y, 
                       x + day_width - TASK_PADDING, 
                       y + height], 
                      fill=color, outline='black')
        draw.text((x + PADDING, y + PADDING), 
                 title, fill='white', font=self.task_font)

    def get_item_color(self, item: Dict[str, Any]) -> str:
        """Get the appropriate color for an item based on its source and status."""
        if item['source'] == 'ticktick':
            return 'gray' if item['completed'] else PRIORITY_COLORS.get(item['priority'], 'black')
        return EVENT_COLORS['google']

    def draw_timestamp(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Draw the current timestamp at the bottom right of the image."""
        timestamp = datetime.now().strftime("%b %d %I:%M %p")
        
        # Calculate text size to position it properly
        if self.timestamp_font:
            text_width = self.timestamp_font.getlength(timestamp)
        else:
            # Approximate width if font loading fails
            text_width = len(timestamp) * 8

        # Position the timestamp at the bottom right
        x = width - text_width - 30
        y = height - 25

        # Draw the timestamp
        draw.text((x, y), timestamp, fill='black', font=self.timestamp_font) 
