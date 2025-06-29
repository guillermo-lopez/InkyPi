import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
import pytz

logger = logging.getLogger(__name__)

# Constants
TICKTICK_API_BASE_URL = "https://api.ticktick.com/open/v1"
TICKTICK_INBOX_PROJECT_ID = "inbox124950952"
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

@dataclass
class TickTickTask:
    """Represents a TickTick task with standardized fields."""
    title: str
    start: datetime
    end: datetime
    is_all_day: bool
    completed: bool
    priority: int
    source: str = 'ticktick'
    
    # Priority colors for tasks
    PRIORITY_COLORS = {
        0: 'blue',   # Normal
        1: 'black',  # Low
        2: 'orange', # Medium
        3: 'pink'    # High
    }
    
    @property
    def color(self) -> str:
        """Get the color for this task based on its priority."""
        return self.PRIORITY_COLORS.get(self.priority, 'blue')

class TickTick:
    """A class to interact with the TickTick API and manage tasks."""
    
    def get_tasks(self, device_config: Any) -> List[TickTickTask]:
        """
        Fetch tasks from TickTick API.
        
        Args:
            device_config: Configuration object containing environment variables
            
        Returns:
            List[TickTickTask]: List of tasks with their metadata
            
        Raises:
            RuntimeError: If API key is not configured or token is invalid
        """
        access_token = device_config.load_env_key("TICKTICK_ACCESS_TOKEN")
        if not access_token:
            raise RuntimeError("TICKTICK API Key not configured.")
     
        if not self._test_token(access_token):
            raise RuntimeError("Invalid access token.")

        # Calculate week start (Sunday) and end (Saturday) in EST
        device_tz = pytz.timezone(device_config.get_config("timezone", "US/Eastern"))
        now = datetime.now(device_tz)
        # weekday() returns 0-6 where 0 is Monday, so we need to adjust for Sunday start
        days_since_sunday = (now.weekday() + 1) % 7  # +1 to shift Monday=0 to Sunday=0
        week_start = now - timedelta(days=days_since_sunday)
        week_end = week_start + timedelta(days=6)

        logger.info(f"Fetching tasks from {week_start} to {week_end} (EST)")

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f'{TICKTICK_API_BASE_URL}/project/{TICKTICK_INBOX_PROJECT_ID}/data',
                headers=headers
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch tasks: {str(e)}")
            raise RuntimeError(f"Failed to fetch tasks: {str(e)}")

        data = response.json()
        if 'tasks' not in data:
            logger.error("Invalid API response format: missing 'tasks' field")
            raise RuntimeError("Invalid API response format: missing 'tasks' field")

        tasks = data['tasks']
        logger.info(f"Retrieved {len(tasks)} tasks from TickTick API")
        
        calendar_tasks = self._organize_tasks_for_calendar(tasks, week_start, device_config)
        logger.info(f"Processed {len(calendar_tasks)} tasks for calendar display")
        
        for task in calendar_tasks:
            logger.info(f"Task: {task.title} - Start: {task.start} - End: {task.end} - All Day: {task.is_all_day}")
        
        return calendar_tasks

    def _test_token(self, access_token: str) -> bool:
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
        
        try:
            response = requests.get(f'{TICKTICK_API_BASE_URL}/project', headers=headers)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Token validation failed: {str(e)}")
            return False
    
    def _organize_tasks_for_calendar(
        self, 
        tasks: List[Dict[str, Any]], 
        week_start: datetime,
        device_config: Any
    ) -> List[TickTickTask]:
        """
        Organize tasks for calendar rendering, extracting start/end times and all-day status.
        
        Args:
            tasks (List[Dict[str, Any]]): List of tasks from the API
            week_start (datetime): Start of the current week
            device_config: Configuration object containing environment variables
            
        Returns:
            List[TickTickTask]: List of tasks with start/end times and other metadata
        """
        calendar_tasks = []
        week_end = week_start + timedelta(days=6)
        
        for task in tasks:
            try:
                processed_task = self._process_single_task(task, week_start, week_end, device_config)
                if processed_task:
                    calendar_tasks.append(processed_task)
            except Exception as e:
                logger.warning(f"Failed to process task {task.get('title', 'Unknown')}: {str(e)}")
                continue
                
        return calendar_tasks

    def _process_single_task(
        self, 
        task: Dict[str, Any], 
        week_start: datetime, 
        week_end: datetime,
        device_config: Any
    ) -> Optional[TickTickTask]:
        """
        Process a single task and convert it to calendar format.
        
        Args:
            task (Dict[str, Any]): The task to process
            week_start (datetime): Start of the current week
            week_end (datetime): End of the current week
            device_config: Configuration object containing environment variables
            
        Returns:
            Optional[TickTickTask]: Processed task or None if task should be skipped
        """
        # Skip if no start or due date
        if not task.get('startDate') and not task.get('dueDate'):
            return None
            
        # Use startDate if available, else dueDate
        start_str = task.get('startDate') or task.get('dueDate')
        end_str = task.get('dueDate') or task.get('startDate')
        
        try:
            start_dt = datetime.strptime(start_str, DATE_FORMAT)
            end_dt = datetime.strptime(end_str, DATE_FORMAT)
            
            # Convert to EST
            device_tz = pytz.timezone(device_config.get_config("timezone", "US/Eastern"))
            start_dt = start_dt.astimezone(device_tz)
            end_dt = end_dt.astimezone(device_tz)
            
            # Only include tasks that overlap with this week
            if end_dt.date() < week_start.date() or start_dt.date() > week_end.date():
                return None
                
            return TickTickTask(
                title=task['title'],
                completed=task.get('status', 0) == 2,
                priority=task.get('priority', 0),
                start=start_dt,
                end=end_dt,
                is_all_day=task.get('isAllDay', False)
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse dates for task {task.get('title', 'Unknown')}: {str(e)}")
            return None
