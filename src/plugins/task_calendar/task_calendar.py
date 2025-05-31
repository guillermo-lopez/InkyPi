from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
from io import BytesIO
import logging
from plugins.task_calendar.services.ticktick import TickTick
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from plugins.task_calendar.services.google_calendar import GoogleCalendar

logger = logging.getLogger(__name__)

class TaskCalendar(BasePlugin):

    # Constants for task display
    PRIORITY_COLORS = {
        0: 'black',   # Normal
        1: 'blue',    # Low
        2: 'orange',  # Medium
        3: 'red'      # High
    }

    # Colors for different event types
    EVENT_COLORS = {
        'google': 'blue',
        'ticktick': 'red'
    }

    def generate_image(self, settings, device_config):
        ticktick = TickTick()
        google_calendar = GoogleCalendar()

        try: 
            tasks = ticktick.get_tasks(device_config)
            events = google_calendar.get_events(device_config)
            
            # Combine tasks and events
            all_items = tasks + events
        except Exception as e:
            logger.error(f"Error getting tasks/events: {e}")
            raise RuntimeError(f"Failed to get tasks/events: {str(e)}")
        
        # Image settings
        display_width = device_config.width if hasattr(device_config, 'width') else 1200
        display_height = device_config.height if hasattr(device_config, 'height') else 800
        
        # Use a smaller width to prevent cutoff
        width = int(display_width * 0.85)  # 85% of the display width
        height = display_height
        image = Image.new('RGB', (display_width, display_height), 'white')  # Use full display dimensions
        draw = ImageDraw.Draw(image)

        # Layout settings
        day_width = width // 7
        header_height = 60  # Increased header height
        task_height = 30
        padding = 5
        task_padding = 2

        # Try to load font, fallback to default if not available
        try:
            header_font = ImageFont.truetype("arial.ttf", 20)
            task_font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            header_font = None
            task_font = None

        # Calculate center offset to center the calendar
        x_offset = (display_width - width) // 2

        # Draw day headers
        today = datetime.now()
        # Calculate days until previous Sunday (0 = Sunday, 1 = Monday, etc.)
        days_to_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_to_sunday)
        
        for i in range(7):
            x = x_offset + i * day_width
            date = week_start + timedelta(days=i)
            day_name = date.strftime('%a')
            day_num = date.strftime('%d')
            draw.rectangle([x, 0, x + day_width, header_height], outline='black', fill='#f7f7f7')
            # Draw day name and number with more spacing
            draw.text((x + padding, padding), day_name, fill='black', font=header_font)
            draw.text((x + padding, padding + 25), day_num, fill='black', font=header_font)

        # Draw vertical grid lines
        for i in range(8):
            x = x_offset + i * day_width
            draw.line([x, header_height, x, height], fill='#cccccc', width=1)

        # Organize items by day
        items_by_day = [[] for _ in range(7)]
        for item in all_items:
            day_idx = (item['start'].date() - week_start.date()).days
            if 0 <= day_idx < 7:
                items_by_day[day_idx].append(item)

        # Sort items by time for each day
        for day_items in items_by_day:
            day_items.sort(key=lambda x: x['start'])

        # Draw items for each day
        for day_idx, day_items in enumerate(items_by_day):
            x = x_offset + day_idx * day_width
            y = header_height + padding

            # Draw all-day items first
            all_day_items = [i for i in day_items if i['is_all_day']]
            for item in all_day_items:
                if item['source'] == 'ticktick':
                    color = 'gray' if item['completed'] else self.PRIORITY_COLORS.get(item['priority'], 'black')
                else:
                    color = self.EVENT_COLORS['google']
                    
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), item['title'][:25], fill='white', font=task_font)
                y += task_height + padding

            # Draw timed items
            timed_items = [i for i in day_items if not i['is_all_day']]
            for item in timed_items:
                if item['source'] == 'ticktick':
                    color = 'gray' if item['completed'] else self.PRIORITY_COLORS.get(item['priority'], 'black')
                else:
                    color = self.EVENT_COLORS['google']
                    
                time_str = item['start'].strftime('%-I:%M %p')
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), f"{time_str} {item['title'][:20]}", fill='white', font=task_font)
                y += task_height + padding

        # Save the image
        image.save('/tmp/calendar.png')
        return image
    
    def _organize_tasks_for_calendar(self, tasks, week_start):
        """
        Organize tasks for calendar rendering, extracting start/end times and all-day status.
        Args:
            tasks (list): List of tasks from the API
            week_start (datetime): Start of the current week
        Returns:
            list: List of tasks with start/end times and other metadata
        """
        calendar_tasks = []
        week_end = week_start + timedelta(days=6)
        for task in tasks:
            # Skip if no start or due date
            if not task.get('startDate') and not task.get('dueDate'):
                continue
            # Use startDate if available, else dueDate
            start_str = task.get('startDate') or task.get('dueDate')
            end_str = task.get('dueDate') or task.get('startDate')
            tz = task.get('timeZone')
            is_all_day = task.get('isAllDay', False)
            try:
                start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                end_dt = datetime.strptime(end_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                # Convert to local timezone if tz is provided
                start_dt = start_dt.astimezone()  # local
                end_dt = end_dt.astimezone()
            except Exception:
                continue
            # Only include tasks that overlap with this week
            if end_dt.date() < week_start.date() or start_dt.date() > week_end.date():
                continue
            calendar_tasks.append({
                'title': task['title'],
                'completed': task.get('status', 0) == 2,
                'priority': task.get('priority', 0),
                'start': start_dt,
                'end': end_dt,
                'is_all_day': is_all_day,
            })
        return calendar_tasks

    def _draw_day_column(self, draw, day_index, day_width, header_height, task_height,
                        week_start, tasks_for_day, max_tasks, show_completed):
        """
        Draw a single day column with its tasks.
        
        Args:
            draw (ImageDraw): Drawing context
            day_index (int): Day index (0-6)
            day_width (int): Width of day column
            header_height (int): Height of header
            task_height (int): Height per task
            week_start (datetime): Start of the week
            tasks_for_day (list): Tasks for this day
            max_tasks (int): Maximum tasks to show
            show_completed (bool): Whether to show completed tasks
        """
        date = week_start + timedelta(days=day_index)
        day_name = date.strftime('%a')
        day_num = date.strftime('%d')
        
        # Draw day header
        x = day_index * day_width
        draw.rectangle([x, 0, x + day_width, header_height], outline='black')
        draw.text((x + 5, 5), f"{day_name}\n{day_num}", fill='black')

        # Draw tasks
        y = header_height + 5
        tasks_shown = 0

        for task in tasks_for_day:
            if not show_completed and task['completed']:
                continue
                
            if tasks_shown >= max_tasks:
                break

            task_color = 'gray' if task['completed'] else self.PRIORITY_COLORS.get(task['priority'], 'black')
            draw.text((x + 5, y), task['title'], fill=task_color)
            y += task_height
            tasks_shown += 1 
