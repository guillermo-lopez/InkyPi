"""
TickTick plugin for InkyPi that displays tasks from TickTick on an e-ink display.
"""
import logging
import requests
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin
from .auth import TickTickAuth

class TickTick(BasePlugin):
    """Plugin to display TickTick tasks on an e-ink display."""

    # Constants for task display
    PRIORITY_COLORS = {
        0: 'black',   # Normal
        1: 'blue',    # Low
        2: 'orange',  # Medium
        3: 'red'      # High
    }

    def generate_settings_template(self):
        """Generate the settings template for the plugin."""
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params

    def get_tasks(self, device_config):
        """
        Fetch tasks from TickTick API.
        
        Args:
            device_config: Configuration object containing environment variables
            
        Returns:
            dict: Tasks organized by day of the week
            
        Raises:
            RuntimeError: If API key is not configured or token is invalid
        """
        access_token = device_config.load_env_key("TICKTICK_ACCESS_TOKEN")
        if not access_token:
            raise RuntimeError("TICKTICK API Key not configured.")
     
        if not self._test_token(access_token):
            raise RuntimeError("Invalid access token.")

        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_end = week_start + timedelta(days=6)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://api.ticktick.com/open/v1/project/inbox124950952/data',
            headers=headers
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch tasks: {response.text}")

        data = response.json()
        if 'tasks' not in data:
            raise RuntimeError("Invalid API response format: missing 'tasks' field")

        return self._organize_tasks_for_calendar(data['tasks'], week_start)

    def _test_token(self, access_token):
        """
        Test if the access token is valid.
        
        Args:
            access_token (str): The access token to test
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://api.ticktick.com/open/v1/project', headers=headers)
        
        logging.info(f"TickTick token test response status: {response.status_code}")
        logging.info(f"TickTick token test response content: {response.text}")
        
        return response.status_code == 200

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

    def generate_image(self, settings, device_config):
        """
        Generate an image displaying the tasks in a calendar-like format with tasks stacked vertically by time.
        """
        try:
            tasks = self.get_tasks(device_config)
        except Exception as e:
            raise RuntimeError(str(e))

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

        # Organize tasks by day
        tasks_by_day = [[] for _ in range(7)]
        for task in tasks:
            day_idx = (task['start'].date() - week_start.date()).days
            if 0 <= day_idx < 7:
                tasks_by_day[day_idx].append(task)

        # Sort tasks by time for each day
        for day_tasks in tasks_by_day:
            day_tasks.sort(key=lambda x: x['start'])

        # Draw tasks for each day
        for day_idx, day_tasks in enumerate(tasks_by_day):
            x = x_offset + day_idx * day_width
            y = header_height + padding

            # Draw all-day tasks first
            all_day_tasks = [t for t in day_tasks if t['is_all_day']]
            for task in all_day_tasks:
                color = 'gray' if task['completed'] else self.PRIORITY_COLORS.get(task['priority'], 'black')
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), task['title'][:25], fill='white', font=task_font)
                y += task_height + padding

            # Draw timed tasks
            timed_tasks = [t for t in day_tasks if not t['is_all_day']]
            for task in timed_tasks:
                color = 'gray' if task['completed'] else self.PRIORITY_COLORS.get(task['priority'], 'black')
                time_str = task['start'].strftime('%-I:%M %p')  # Changed to 12-hour format with AM/PM
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), f"{time_str} {task['title'][:20]}", fill='white', font=task_font)
                y += task_height + padding

        # Save the image
        image.save('/tmp/ticktick_calendar.png')
        return image

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
