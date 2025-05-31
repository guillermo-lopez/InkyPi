from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw
import logging
from typing import Dict, Any, Optional
from plugins.task_calendar.services.ticktick import TickTick
from plugins.task_calendar.services.google_calendar import GoogleCalendar
from .ui.renderer import CalendarRenderer
from .ui.layout import calculate_calendar_dimensions
from .ui.styles import CALENDAR_WIDTH_RATIO

logger = logging.getLogger(__name__)

class CalendarError(Exception):
    """Base exception for calendar-related errors."""
    pass

class TaskCalendar(BasePlugin):
    """A plugin that displays tasks and calendar events in a weekly view."""

    def __init__(self, plugin_config: Dict[str, Any] = None):
        """
        Initialize the TaskCalendar plugin.
        
        Args:
            plugin_config: Plugin configuration dictionary
        """
        super().__init__(plugin_config)
        self._ticktick: Optional[TickTick] = None
        self._google_calendar: Optional[GoogleCalendar] = None
        self._renderer = CalendarRenderer()

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
            
            # Calculate calendar dimensions
            width, height, day_width, x_offset = calculate_calendar_dimensions(
                display_width, display_height, CALENDAR_WIDTH_RATIO
            )
            
            # Create image and drawing context
            image = Image.new('RGB', (display_width, display_height), 'white')
            draw = ImageDraw.Draw(image)

            # Draw calendar structure
            self._renderer.draw_calendar_structure(draw, x_offset, day_width, height)
            
            # Draw items
            self._renderer.draw_calendar_items(draw, all_items, x_offset, day_width)

            # Draw timestamp
            self._renderer.draw_timestamp(draw, display_width, display_height)

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
