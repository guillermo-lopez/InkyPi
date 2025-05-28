"""
Calendar plugin for InkyPi that displays events from Google Calendar and tasks from TickTick.
"""
import logging
import requests
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin
# from .google_auth import authenticate as authenticate_google
from .ticktick_auth import authenticate as authenticate_ticktick
# from googleapiclient.discovery import build

class Calendar(BasePlugin):
    """Plugin to display Google Calendar events and TickTick tasks on an e-ink display."""

    # Constants for task display
    PRIORITY_COLORS = {
        0: 'black',   # Normal
        1: 'blue',    # Low
        2: 'orange',  # Medium
        3: 'red'      # High
    }

    # Colors for different event types
    EVENT_COLORS = {
        # 'google': 'blue',
        'ticktick': 'red'
    }

    def generate_settings_template(self):
        """Generate the settings template for the plugin."""
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params

    # def get_google_events(self, credentials):
    #     """
    #     Fetch events from Google Calendar API.
    #     
    #     Args:
    #         credentials: Google Calendar credentials object
    #         
    #     Returns:
    #         list: List of events with start/end times and other metadata
    #         
    #     Raises:
    #         RuntimeError: If API call fails
    #     """
    #     try:
    #         service = build('calendar', 'v3', credentials=credentials)
    #         
    #         # Get the current week's start and end
    #         now = datetime.now()
    #         week_start = now - timedelta(days=now.weekday())
    #         week_end = week_start + timedelta(days=6)
    #         
    #         # Format dates for Google Calendar API
    #         time_min = week_start.isoformat() + 'Z'
    #         time_max = week_end.isoformat() + 'Z'
    #         
    #         events_result = service.events().list(
    #             calendarId='primary',
    #             timeMin=time_min,
    #             timeMax=time_max,
    #             singleEvents=True,
    #             orderBy='startTime'
    #         ).execute()
    #         
    #         events = events_result.get('items', [])
    #         
    #         # Process events into a consistent format
    #         calendar_events = []
    #         for event in events:
    #             start = event['start'].get('dateTime', event['start'].get('date'))
    #             end = event['end'].get('dateTime', event['end'].get('date'))
    #             
    #             # Convert to datetime objects
    #             if 'T' in start:  # Has time component
    #                 start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
    #                 end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
    #                 is_all_day = False
    #             else:  # All-day event
    #                 start_dt = datetime.fromisoformat(start)
    #                 end_dt = datetime.fromisoformat(end)
    #                 is_all_day = True
    #             
    #             calendar_events.append({
    #                 'title': event['summary'],
    #                 'start': start_dt,
    #                 'end': end_dt,
    #                 'is_all_day': is_all_day,
    #                 'source': 'google',
    #                 'color': event.get('colorId', 'blue')  # Use Google Calendar color if available
    #             })
    #         
    #         return calendar_events
    #         
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to fetch Google Calendar events: {str(e)}")

    def get_ticktick_tasks(self, auth):
        """
        Fetch tasks from TickTick API.
        
        Args:
            auth: TickTickAuth object
            
        Returns:
            list: List of tasks with start/end times and other metadata
            
        Raises:
            RuntimeError: If API call fails
        """
        tokens = auth.load_tokens()
        if not tokens or 'access_token' not in tokens:
            raise RuntimeError("No valid TickTick access token found.")
        
        access_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://api.ticktick.com/open/v1/project/inbox124950952/data',
            headers=headers
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch TickTick tasks: {response.text}")

        data = response.json()
        if 'tasks' not in data:
            raise RuntimeError("Invalid API response format: missing 'tasks' field")

        return self._organize_ticktick_tasks(data['tasks'])

    def _organize_ticktick_tasks(self, tasks):
        """
        Organize TickTick tasks for calendar rendering.
        
        Args:
            tasks (list): List of tasks from the API
            
        Returns:
            list: List of tasks with start/end times and other metadata
        """
        calendar_tasks = []
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_end = week_start + timedelta(days=6)
        
        for task in tasks:
            # Skip if no start or due date
            if not task.get('startDate') and not task.get('dueDate'):
                continue
                
            # Use startDate if available, else dueDate
            start_str = task.get('startDate') or task.get('dueDate')
            end_str = task.get('dueDate') or task.get('startDate')
            is_all_day = task.get('isAllDay', False)
            
            try:
                start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                end_dt = datetime.strptime(end_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                # Convert to local timezone
                start_dt = start_dt.astimezone()
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
                'source': 'ticktick'
            })
            
        return calendar_tasks

    def generate_image(self, settings, device_config):
        """
        Generate an image displaying the events and tasks in a calendar-like format.
        """
        try:
            # Authenticate with both services
            # google_auth = authenticate_google()
            ticktick_auth = authenticate_ticktick()
            
            # if not google_auth or not ticktick_auth:
            if not ticktick_auth:
                raise RuntimeError("Failed to authenticate with one or more services")
            
            # Get events and tasks
            # google_events = self.get_google_events(google_auth.load_tokens())
            ticktick_tasks = self.get_ticktick_tasks(ticktick_auth)
            
            # Combine all events and tasks
            # all_events = google_events + ticktick_tasks
            all_events = ticktick_tasks
            
        except Exception as e:
            raise RuntimeError(str(e))

        # Image settings
        display_width = device_config.width if hasattr(device_config, 'width') else 1200
        display_height = device_config.height if hasattr(device_config, 'height') else 800
        
        # Use a smaller width to prevent cutoff
        width = int(display_width * 0.85)  # 85% of the display width
        height = display_height
        image = Image.new('RGB', (display_width, display_height), 'white')
        draw = ImageDraw.Draw(image)

        # Layout settings
        day_width = width // 7
        header_height = 60
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

        # Organize events by day
        events_by_day = [[] for _ in range(7)]
        for event in all_events:
            day_idx = (event['start'].date() - week_start.date()).days
            if 0 <= day_idx < 7:
                events_by_day[day_idx].append(event)

        # Sort events by time for each day
        for day_events in events_by_day:
            day_events.sort(key=lambda x: x['start'])

        # Draw events for each day
        for day_idx, day_events in enumerate(events_by_day):
            x = x_offset + day_idx * day_width
            y = header_height + padding

            # Draw all-day events first
            all_day_events = [e for e in day_events if e['is_all_day']]
            for event in all_day_events:
                if event['source'] == 'ticktick':
                    color = 'gray' if event['completed'] else self.PRIORITY_COLORS.get(event['priority'], 'black')
                # else:
                #     color = self.EVENT_COLORS['google']
                    
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), event['title'][:25], fill='white', font=task_font)
                y += task_height + padding

            # Draw timed events
            timed_events = [e for e in day_events if not e['is_all_day']]
            for event in timed_events:
                if event['source'] == 'ticktick':
                    color = 'gray' if event['completed'] else self.PRIORITY_COLORS.get(event['priority'], 'black')
                # else:
                #     color = self.EVENT_COLORS['google']
                    
                time_str = event['start'].strftime('%-I:%M %p')
                draw.rectangle([x + task_padding, y, x + day_width - task_padding, y + task_height], 
                             fill=color, outline='black')
                draw.text((x + padding, y + padding), f"{time_str} {event['title'][:20]}", fill='white', font=task_font)
                y += task_height + padding

        # Save the image
        image.save('/tmp/calendar.png')
        return image 
