"""Calendar layout calculations and positioning."""

from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Union
from ..services.google_calendar import CalendarEvent
from ..services.ticktick import TickTickTask

def calculate_week_start() -> datetime:
    """Calculate the start of the current week (Sunday)."""
    today = datetime.now()
    days_to_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_to_sunday)

def calculate_day_index(date: datetime, week_start: datetime) -> int:
    """Calculate the day index (0-6) for a given date."""
    return (date.date() - week_start.date()).days

def calculate_item_height(item: Union[CalendarEvent, TickTickTask], base_height: int) -> int:
    """
    Calculate the height of an item based on its duration.
    
    Args:
        item: Calendar item (either CalendarEvent or TickTickTask)
        base_height: Base height for a standard item
        
    Returns:
        Height in pixels
    """
    if item.is_all_day:
        return base_height
        
    # Calculate duration in minutes
    try:
        duration = item.end - item.start
        duration_minutes = duration.total_seconds() / 60
    except (TypeError, AttributeError):
        # If duration can't be calculated, use minimum height
        return base_height
        
    # Round up to nearest 30 minutes, with a minimum of 30 minutes
    duration_blocks = max(1, (duration_minutes + 29) // 30)
    return int(base_height * duration_blocks)

def calculate_calendar_dimensions(display_width: int, display_height: int, 
                                width_ratio: float) -> Tuple[int, int, int, int]:
    """
    Calculate calendar dimensions and offsets.
    
    Args:
        display_width: Total display width
        display_height: Total display height
        width_ratio: Ratio of calendar width to display width
        
    Returns:
        Tuple of (calendar_width, calendar_height, day_width, x_offset)
    """
    calendar_width = int(display_width * width_ratio)
    calendar_height = display_height
    day_width = calendar_width // 7
    x_offset = (display_width - calendar_width) // 2
    
    return calendar_width, calendar_height, day_width, x_offset 
