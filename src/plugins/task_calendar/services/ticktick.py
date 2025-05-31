import logging
import requests
from datetime import datetime, timedelta

class TickTick():
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
                'source': 'ticktick'
            })
        return calendar_tasks
