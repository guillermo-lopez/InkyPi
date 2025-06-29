"""Calendar rendering and drawing functionality."""

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import textwrap

from .styles import (
    HEADER_HEIGHT, TASK_HEIGHT, PADDING, TASK_PADDING,
    DEFAULT_FONT_SIZE, DEFAULT_TASK_FONT_SIZE,
    TIMESTAMP_FONT_SIZE, MAX_TITLE_LENGTH, MAX_TIMED_TITLE_LENGTH,
    LINE_HEIGHT, FONT_PATH
)
from .layout import calculate_week_start, calculate_day_index, calculate_item_height
from ..services.google_calendar import CalendarEvent
from ..services.ticktick import TickTickTask

logger = logging.getLogger(__name__)

class CalendarRenderer:
    """Handles the rendering of calendar elements."""

    FONT_NAME = "DejaVuSans.ttf"  # No longer used, use FONT_PATH instead

    def __init__(self):
        """Initialize the calendar renderer."""
        self.header_font = None
        self.task_font = None
        self.timestamp_font = None
        self._load_fonts()

    def _load_fonts(self) -> None:
        """Load fonts for calendar display with fallback to default."""
        try:
            self.header_font = ImageFont.truetype(FONT_PATH, DEFAULT_FONT_SIZE)
            self.task_font = ImageFont.truetype(FONT_PATH, DEFAULT_TASK_FONT_SIZE)
            self.timestamp_font = ImageFont.truetype(FONT_PATH, TIMESTAMP_FONT_SIZE)
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
            
            # Use gray background for current day
            is_today = date.date() == today.date()
            header_color = '#666666' if is_today else '#f7f7f7'
            text_color = 'white' if is_today else 'black'
            
            draw.rectangle([x, 0, x + day_width, HEADER_HEIGHT], 
                         outline='black', fill=header_color)
            draw.text((x + PADDING, PADDING), day_name, 
                     fill=text_color, font=self.header_font)
            draw.text((x + PADDING, PADDING + 25), day_num, 
                     fill=text_color, font=self.header_font)

        # Draw vertical grid lines
        for i in range(8):
            x = x_offset + i * day_width
            draw.line([x, HEADER_HEIGHT, x, height], 
                     fill='#cccccc', width=1)

    def draw_calendar_items(self, draw: ImageDraw.Draw, 
                          items: List[Union[CalendarEvent, TickTickTask]], 
                          x_offset: int, day_width: int) -> None:
        """Draw tasks and events on the calendar."""
        week_start = calculate_week_start()

        # Organize items by day
        items_by_day: List[List[Union[CalendarEvent, TickTickTask]]] = [[] for _ in range(7)]
        for item in items:
            # Handle multi-day events
            current_date = item.start
            while current_date <= item.end and current_date.date() <= (week_start + timedelta(days=6)).date():
                day_idx = calculate_day_index(current_date, week_start)
                if 0 <= day_idx < 7:
                    items_by_day[day_idx].append(item)
                current_date += timedelta(days=1)

        # Sort and draw items for each day
        for day_idx, day_items in enumerate(items_by_day):
            # Sort by all-day first, then by start time
            day_items.sort(key=lambda x: (not x.is_all_day, x.start))
            self.draw_day_items(draw, day_idx, day_items, x_offset, day_width)

    def calculate_item_height(self, item: Union[CalendarEvent, TickTickTask], base_height: int) -> int:
        """Calculate the height of an item based on its duration."""
        if item.is_all_day:
            return base_height
            
        duration = item.end - item.start
        duration_hours = duration.total_seconds() / 3600
        
        if duration_hours <= 3:
            # For events under 3 hours, increase height for every 30 minutes
            # Each 30-minute increment adds one base_height
            thirty_min_blocks = int(duration_hours * 2)  # Convert hours to 30-min blocks
            return base_height * (thirty_min_blocks + 1)  # +1 for minimum height
        else:
            # For longer events, use standard height
            return base_height

    def draw_day_items(self, draw: ImageDraw.Draw, day_idx: int, 
                      day_items: List[Union[CalendarEvent, TickTickTask]], 
                      x_offset: int, day_width: int) -> None:
        """Draw items for a specific day."""
        x = x_offset + day_idx * day_width
        y = HEADER_HEIGHT + PADDING

        # Draw all-day items first
        all_day_items = [i for i in day_items if i.is_all_day]
        for item in all_day_items:
            color = self.get_item_color(item)
            self.draw_item(draw, item, x, y, day_width, color)
            y += TASK_HEIGHT + PADDING

        # Draw timed items
        timed_items = [i for i in day_items if not i.is_all_day]
        for item in timed_items:
            color = self.get_item_color(item)
            time_str = item.start.strftime('%-I:%M %p')
            title = f"{time_str} {item.title[:MAX_TIMED_TITLE_LENGTH]}"
            item_height = self.calculate_item_height(item, TASK_HEIGHT)
            self.draw_item(draw, item, x, y, day_width, color, title, item_height)
            y += item_height + PADDING

    def get_font_color(self, background_color: str) -> str:
        """Determine the appropriate font color based on the background color.
        
        Args:
            background_color: The hex color code of the background
            
        Returns:
            'black' for light backgrounds, 'white' for dark backgrounds
        """
        # Colors that should use black font
        light_colors = {
            'yellow',
        }
        
        return 'black' if background_color.lower() in light_colors else 'white'

    def draw_item(self, draw: ImageDraw.Draw, 
                 item: Union[CalendarEvent, TickTickTask], 
                 x: int, y: int, day_width: int, color: str, 
                 title: Optional[str] = None, height: Optional[int] = None) -> None:
        """Draw a single calendar item with text wrapping."""
        if title is None:
            title = item.title[:MAX_TITLE_LENGTH]
            
        if height is None:
            height = TASK_HEIGHT
            
        # Calculate available width for text
        text_width = day_width - (2 * PADDING + 2 * TASK_PADDING)
        
        # Wrap text to fit available width
        if self.task_font:
            # Estimate characters per line based on font size
            chars_per_line = int(text_width / (DEFAULT_TASK_FONT_SIZE * 0.6))  # Approximate character width
            wrapped_text = textwrap.wrap(title, width=chars_per_line)
        else:
            # Fallback if font loading fails
            wrapped_text = [title]
            
        # Calculate required height based on number of lines
        required_height = max(height, len(wrapped_text) * LINE_HEIGHT)
        
        # Draw the background rectangle
        draw.rectangle([x + TASK_PADDING, y, 
                       x + day_width - TASK_PADDING, 
                       y + required_height], 
                      fill=color, outline='black')
        
        # Draw wrapped text
        font_color = self.get_font_color(color)
        current_y = y + PADDING
        for line in wrapped_text:
            draw.text((x + PADDING, current_y), 
                     line, fill=font_color, font=self.task_font)
            current_y += LINE_HEIGHT

    def get_item_color(self, item: Union[CalendarEvent, TickTickTask]) -> str:
        """Get the appropriate color for an item based on its source and status."""
        if isinstance(item, TickTickTask):
            return 'gray' if item.completed else item.color
        return item.color

    def draw_timestamp(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Draw the current timestamp at the bottom right of the image."""
        timestamp = datetime.now().strftime("%b %d - %I:%M %p")
        
        # Calculate text size to position it properly
        if self.timestamp_font:
            text_width = self.timestamp_font.getlength(timestamp)
        else:
            # Approximate width if font loading fails
            text_width = len(timestamp) * 8

        # Position the timestamp at the bottom right
        x = width - text_width - 70
        y = height - 25

        # Draw the timestamp
        draw.text((x, y), timestamp, fill='black', font=self.timestamp_font) 
