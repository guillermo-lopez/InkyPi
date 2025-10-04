from googleapiclient.discovery import build
import logging
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pytz
from ..auth.google_auth import GoogleCalendarAuth

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Represents a calendar event with standardized fields."""
    title: str
    start: datetime
    end: datetime
    is_all_day: bool
    source: str = 'google'
    calendar_name: str = 'primary'
    
    # Default colors for different calendars
    CALENDAR_COLORS = {
        'primary': 'red',
        'other_google': 'blue',
        'events_available': 'purple',
        'holidays': 'green',
        'birthdays': 'orange',
        'partiful': 'green',
        'work': 'yellow',
    }
    
    @property
    def color(self) -> str:
        """Get the color for this event based on its calendar."""
        return self.CALENDAR_COLORS.get(self.calendar_name, 'blue')

class GoogleCalendar:
    """Service class for interacting with Google Calendar API."""
    
    def __init__(self):
        self.service = None
        self._credentials: Optional[Credentials] = None
        self._calendar_ids: Dict[str, str] = {}
        self._auth: Optional[GoogleCalendarAuth] = None
        self._load_calendar_ids()

    def _load_calendar_ids(self) -> None:
        """Load calendar IDs from environment variables."""
        load_dotenv()
        
        # Load primary calendar ID
        primary_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self._calendar_ids['primary'] = primary_id
        
        # Load additional calendar IDs
        calendar_prefix = 'GOOGLE_CALENDAR_ID_'
        for key, value in os.environ.items():
            if key.startswith(calendar_prefix):
                calendar_name = key[len(calendar_prefix):].lower()
                self._calendar_ids[calendar_name] = value
        
        logger.info(f"Loaded {len(self._calendar_ids)} calendar IDs")

    def _initialize_auth(self) -> None:
        """Initialize the Google Calendar authentication."""
        if self._auth:
            return
            
        load_dotenv()
        client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise RuntimeError(
                "GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET "
                "must be set in .env file"
            )
        
        self._auth = GoogleCalendarAuth(client_id, client_secret)

    def _initialize_service(self, force_refresh: bool = False) -> None:
        """Initialize the Google Calendar service with credentials."""
        if self.service and not force_refresh:
            return

        self._initialize_auth()

        # Get valid credentials (with automatic refresh if needed)
        self._credentials = self._auth.get_valid_credentials()
        if not self._credentials:
            raise RuntimeError(
                "No valid Google Calendar credentials found. "
                "Please run the authentication script to set up credentials:\n"
                "python3 src/plugins/task_calendar/auth/google_auth.py"
            )

        self.service = build('calendar', 'v3', credentials=self._credentials)

    def _parse_event_datetime(self, dt_str: str) -> tuple[datetime, bool]:
        """Parse event datetime string and determine if it's an all-day event."""
        if 'T' in dt_str:  # Has time component
            # Parse the ISO format string and ensure it's timezone-aware
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, False
        # For all-day events, use midnight UTC
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
        return dt, True

    def _format_event(self, event: Dict[str, Any], calendar_name: str) -> CalendarEvent:
        """Convert Google Calendar event to standardized format."""
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        start_dt, is_all_day = self._parse_event_datetime(start)
        end_dt, _ = self._parse_event_datetime(end)
        
        # Convert to EST
        est = pytz.timezone('US/Eastern')
        start_dt = start_dt.astimezone(est)
        end_dt = end_dt.astimezone(est)
        
        return CalendarEvent(
            title=event['summary'],
            start=start_dt,
            end=end_dt,
            is_all_day=is_all_day,
            calendar_name=calendar_name
        )

    def get_events(self, device_config: Any) -> List[CalendarEvent]:
        """
        Fetch events from multiple Google Calendars.
        
        Args:
            device_config: Configuration object containing environment variables
            
        Returns:
            List[CalendarEvent]: List of calendar events from all configured calendars
            
        Raises:
            RuntimeError: If API call fails or credentials are invalid
        """
        try:
            self._initialize_service()
            
            # Get the current week's start and end in EST
            device_tz = pytz.timezone(device_config.get_config("timezone", "US/Eastern"))
            now = datetime.now(device_tz)
            # Calculate week start (Sunday) and end (Saturday)
            # weekday() returns 0-6 where 0 is Monday, so we need to adjust for Sunday start
            days_since_sunday = (now.weekday() + 1) % 7  # +1 to shift Monday=0 to Sunday=0
            week_start = now - timedelta(days=days_since_sunday)
            week_end = week_start + timedelta(days=6)
            
            # Format dates for Google Calendar API (convert to UTC for API)
            time_min = week_start.astimezone(pytz.UTC).isoformat()
            time_max = week_end.astimezone(pytz.UTC).isoformat()
            
            logger.info(f"Fetching events from {time_min} to {time_max} (EST: {week_start} to {week_end})")
            
            all_events = []
            
            # Fetch events from each calendar
            for calendar_name, calendar_id in self._calendar_ids.items():
                try:
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    calendar_events = [self._format_event(event, calendar_name) for event in events]
                    all_events.extend(calendar_events)
                    
                    logger.info(f"Retrieved {len(calendar_events)} events from calendar: {calendar_name}")
                    for event in calendar_events:
                        logger.info(f"Event: {event.title} - Start: {event.start} - End: {event.end} - All Day: {event.is_all_day}")
                except Exception as e:
                    error_msg = str(e)
                    if "invalid_grant" in error_msg or "Token has been expired or revoked" in error_msg:
                        logger.error(f"Authentication error for calendar {calendar_name}: {e}")
                        logger.error("Token refresh failed. Invalidating cached service and retrying with fresh credentials...")

                        # Invalidate cached service and credentials
                        self.service = None
                        self._credentials = None

                        # Try to re-initialize with fresh credentials from disk
                        try:
                            self._initialize_service(force_refresh=True)

                            # Retry the API call with fresh credentials
                            events_result = self.service.events().list(
                                calendarId=calendar_id,
                                timeMin=time_min,
                                timeMax=time_max,
                                singleEvents=True,
                                orderBy='startTime'
                            ).execute()

                            events = events_result.get('items', [])
                            calendar_events = [self._format_event(event, calendar_name) for event in events]
                            all_events.extend(calendar_events)

                            logger.info(f"Successfully retrieved {len(calendar_events)} events after credential refresh")
                            for event in calendar_events:
                                logger.info(f"Event: {event.title} - Start: {event.start} - End: {event.end} - All Day: {event.is_all_day}")
                        except Exception as retry_error:
                            logger.error(f"Failed to fetch events even after credential refresh: {retry_error}")
                            logger.error("Please re-authenticate by running: python3 src/plugins/task_calendar/auth/google_auth.py")
                            raise RuntimeError(f"Google Calendar authentication failed: {error_msg}")
                    else:
                        logger.error(f"Error fetching events from calendar {calendar_name}: {e}")
                        continue
            
            return all_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            raise RuntimeError(f"Failed to fetch Google Calendar events: {str(e)}")
