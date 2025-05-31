from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from plugins.task_calendar.services.ticktick import TickTick
from plugins.task_calendar.services.google_calendar import GoogleCalendar

logger = logging.getLogger(__name__)

class CalendarError(Exception):
    """Base exception for calendar-related errors."""
    pass

class TaskCalendar(BasePlugin):
    """A plugin that displays tasks and calendar events in a weekly view."""

    # Display constants
    PRIORITY_COLORS: Dict[int, str] = {
        0: 'black',   # Normal
        1: 'blue',    # Low
        2: 'orange',  # Medium
        3: 'pink'      # High
    }

    EVENT_COLORS: Dict[str, str] = {
        'google': '#4285F4',  # Google blue
        'ticktick': '#FF5722'  # TickTick orange
    }

    # Layout constants
    HEADER_HEIGHT: int = 60
    TASK_HEIGHT: int = 30
    PADDING: int = 5
    TASK_PADDING: int = 2
    CALENDAR_WIDTH_RATIO: float = 0.85  # 85% of display width
    DEFAULT_FONT_SIZE: int = 20
    DEFAULT_TASK_FONT_SIZE: int = 16
    TIMESTAMP_FONT_SIZE: int = 14
    MAX_TITLE_LENGTH: int = 25
    MAX_TIMED_TITLE_LENGTH: int = 20

    def __init__(self, plugin_config: Dict[str, Any] = None):
        """
        Initialize the TaskCalendar plugin.
        
        Args:
            plugin_config: Plugin configuration dictionary
        """
        super().__init__(plugin_config)
        self._ticktick: Optional[TickTick] = None
        self._google_calendar: Optional[GoogleCalendar] = None

    def generate_image(self, settings: Dict[str, Any], device_config: Any) -> Image.Image:
        """
        Generate a weekly calendar view image with tasks and events.
        
        Args:
            settings: Plugin settings
            device_config: Device configuration
            
        Returns:
            PIL.Image: Generated calendar image
            
        Raises:
            CalendarError: If tasks/events cannot be retrieved or image generation fails
        """
        try:
            # Initialize services
            self._initialize_services()

            # Get tasks and events
            tasks = self._ticktick.get_tasks(device_config)
            events = self._google_calendar.get_events(device_config)
            all_items = tasks + events

            # Setup image dimensions with defaults
            display_width = getattr(device_config, 'width', 1200)
            display_height = getattr(device_config, 'height', 800)
            width = int(display_width * self.CALENDAR_WIDTH_RATIO)
            height = display_height
            
            # Create image and drawing context
            image = Image.new('RGB', (display_width, display_height), 'white')
            draw = ImageDraw.Draw(image)

            # Calculate layout
            day_width = width // 7
            x_offset = (display_width - width) // 2

            # Load fonts
            header_font, task_font = self._load_fonts()

            # Draw calendar structure
            self._draw_calendar_structure(draw, x_offset, day_width, header_font, height)
            
            # Draw items
            self._draw_calendar_items(draw, all_items, x_offset, day_width, task_font)

            # Draw timestamp
            self._draw_timestamp(draw, display_width, display_height)

            # Save and return image
            image.save('/tmp/calendar.png')
            return image

        except Exception as e:
            logger.error(f"Error generating calendar image: {e}")
            raise CalendarError(f"Failed to generate calendar image: {str(e)}")

    def _initialize_services(self) -> None:
        """Initialize calendar services if not already initialized."""
        if self._ticktick is None:
            self._ticktick = TickTick()
        if self._google_calendar is None:
            self._google_calendar = GoogleCalendar()

    def _load_fonts(self) -> Tuple[Optional[ImageFont.FreeTypeFont], Optional[ImageFont.FreeTypeFont]]:
        """
        Load fonts for calendar display with fallback to default.
        
        Returns:
            Tuple of (header_font, task_font)
        """
        try:
            header_font = ImageFont.truetype("arial.ttf", self.DEFAULT_FONT_SIZE)
            task_font = ImageFont.truetype("arial.ttf", self.DEFAULT_TASK_FONT_SIZE)
        except Exception as e:
            logger.warning(f"Failed to load custom fonts: {e}. Using default fonts.")
            header_font = None
            task_font = None
        return header_font, task_font

    def _draw_calendar_structure(self, draw: ImageDraw.Draw, x_offset: int, day_width: int, 
                               header_font: Optional[ImageFont.FreeTypeFont], height: int) -> None:
        """
        Draw the basic calendar structure including headers and grid lines.
        
        Args:
            draw: Drawing context
            x_offset: X offset for centering
            day_width: Width of each day column
            header_font: Font for header text
            height: Total height of the image
        """
        today = datetime.now()
        days_to_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_to_sunday)

        # Draw day headers
        for i in range(7):
            x = x_offset + i * day_width
            date = week_start + timedelta(days=i)
            day_name = date.strftime('%a')
            day_num = date.strftime('%d')
            
            # Use yellow background for current day
            is_today = date.date() == today.date()
            header_color = '#ffff00' if is_today else '#f7f7f7'
            
            draw.rectangle([x, 0, x + day_width, self.HEADER_HEIGHT], 
                         outline='black', fill=header_color)
            draw.text((x + self.PADDING, self.PADDING), day_name, 
                     fill='black', font=header_font)
            draw.text((x + self.PADDING, self.PADDING + 25), day_num, 
                     fill='black', font=header_font)

        # Draw vertical grid lines
        for i in range(8):
            x = x_offset + i * day_width
            draw.line([x, self.HEADER_HEIGHT, x, height], 
                     fill='#cccccc', width=1)

    def _draw_calendar_items(self, draw: ImageDraw.Draw, items: List[Dict[str, Any]], 
                           x_offset: int, day_width: int, task_font: Optional[ImageFont.FreeTypeFont]) -> None:
        """
        Draw tasks and events on the calendar.
        
        Args:
            draw: Drawing context
            items: List of calendar items to draw
            x_offset: X offset for centering
            day_width: Width of each day column
            task_font: Font for task text
        """
        today = datetime.now()
        days_to_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_to_sunday)

        # Organize items by day
        items_by_day: List[List[Dict[str, Any]]] = [[] for _ in range(7)]
        for item in items:
            day_idx = (item['start'].date() - week_start.date()).days
            if 0 <= day_idx < 7:
                items_by_day[day_idx].append(item)

        # Sort and draw items for each day
        for day_idx, day_items in enumerate(items_by_day):
            day_items.sort(key=lambda x: x['start'])
            self._draw_day_items(draw, day_idx, day_items, x_offset, day_width, task_font)

    def _draw_day_items(self, draw: ImageDraw.Draw, day_idx: int, day_items: List[Dict[str, Any]], 
                       x_offset: int, day_width: int, task_font: Optional[ImageFont.FreeTypeFont]) -> None:
        """
        Draw items for a specific day.
        
        Args:
            draw: Drawing context
            day_idx: Index of the day (0-6)
            day_items: List of items for this day
            x_offset: X offset for centering
            day_width: Width of each day column
            task_font: Font for task text
        """
        x = x_offset + day_idx * day_width
        y = self.HEADER_HEIGHT + self.PADDING

        # Draw all-day items first
        all_day_items = [i for i in day_items if i['is_all_day']]
        for item in all_day_items:
            color = self._get_item_color(item)
            self._draw_item(draw, item, x, y, day_width, color, task_font)
            y += self.TASK_HEIGHT + self.PADDING

        # Draw timed items
        timed_items = [i for i in day_items if not i['is_all_day']]
        for item in timed_items:
            color = self._get_item_color(item)
            time_str = item['start'].strftime('%-I:%M %p')
            title = f"{time_str} {item['title'][:self.MAX_TIMED_TITLE_LENGTH]}"
            item_height = self._calculate_item_height(item)
            self._draw_item(draw, item, x, y, day_width, color, task_font, title, item_height)
            y += item_height + self.PADDING

    def _calculate_item_height(self, item: Dict[str, Any]) -> int:
        """
        Calculate the height of an item based on its duration.
        
        Args:
            item: Calendar item dictionary
            
        Returns:
            Height in pixels
        """
        if item['is_all_day']:
            return self.TASK_HEIGHT
            
        # Calculate duration in minutes
        try:
            duration = item['end'] - item['start']
            duration_minutes = duration.total_seconds() / 60
        except (TypeError, AttributeError):
            # If duration can't be calculated, use minimum height
            return self.TASK_HEIGHT
            
        # Round up to nearest 30 minutes, with a minimum of 30 minutes
        duration_blocks = max(1, (duration_minutes + 29) // 30)
        return int(self.TASK_HEIGHT * duration_blocks)

    def _draw_item(self, draw: ImageDraw.Draw, item: Dict[str, Any], x: int, y: int, 
                  day_width: int, color: str, task_font: Optional[ImageFont.FreeTypeFont], 
                  title: Optional[str] = None, height: Optional[int] = None) -> None:
        """
        Draw a single calendar item.
        
        Args:
            draw: Drawing context
            item: Calendar item dictionary
            x: X coordinate
            y: Y coordinate
            day_width: Width of the day column
            color: Color for the item
            task_font: Font for the item text
            title: Optional custom title (if None, uses item title)
            height: Optional custom height (if None, uses default TASK_HEIGHT)
        """
        if title is None:
            title = item['title'][:self.MAX_TITLE_LENGTH]
            
        if height is None:
            height = self.TASK_HEIGHT
            
        draw.rectangle([x + self.TASK_PADDING, y, 
                       x + day_width - self.TASK_PADDING, 
                       y + height], 
                      fill=color, outline='black')
        draw.text((x + self.PADDING, y + self.PADDING), 
                 title, fill='white', font=task_font)

    def _get_item_color(self, item: Dict[str, Any]) -> str:
        """
        Get the appropriate color for an item based on its source and status.
        
        Args:
            item: Calendar item dictionary
            
        Returns:
            Color string for the item
        """
        if item['source'] == 'ticktick':
            return 'gray' if item['completed'] else self.PRIORITY_COLORS.get(item['priority'], 'black')
        return self.EVENT_COLORS['google']

    def _draw_timestamp(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """
        Draw the current timestamp at the bottom right of the image.
        
        Args:
            draw: Drawing context
            width: Width of the image
            height: Height of the image
        """
        try:
            # Load a smaller font for the timestamp
            timestamp_font = ImageFont.truetype("arial.ttf", self.TIMESTAMP_FONT_SIZE)
        except Exception:
            timestamp_font = None

        # Format the current time
        timestamp = datetime.now().strftime("%b %d %I:%M %p")
        
        # Calculate text size to position it properly
        if timestamp_font:
            text_width = timestamp_font.getlength(timestamp)
        else:
            # Approximate width if font loading fails
            text_width = len(timestamp) * 8

        # Position the timestamp at the bottom right with more left padding
        x = width - text_width - 30
        y = height - 25

        # Draw the timestamp
        draw.text((x, y), timestamp, fill='black', font=timestamp_font) 
