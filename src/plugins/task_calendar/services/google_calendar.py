from googleapiclient.discovery import build
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import os
import json
from google.auth.transport.requests import Request
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Represents a calendar event with standardized fields."""
    title: str
    start: datetime
    end: datetime
    is_all_day: bool
    source: str = 'google'
    color: str = 'blue'

class GoogleCalendar:
    """Service class for interacting with Google Calendar API."""
    
    def __init__(self):
        self.service = None
        self._credentials: Optional[Credentials] = None

    def _load_credentials_from_env(self) -> Optional[Credentials]:
        """Load credentials from environment variables."""
        load_dotenv()
        access_token = os.getenv('GOOGLE_CALENDAR_ACCESS_TOKEN')
        client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
        refresh_token = os.getenv('GOOGLE_CALENDAR_REFRESH_TOKEN')

        if not all([access_token, client_id, client_secret]):
            return None

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )

        if refresh_token:
            try:
                credentials.refresh(Request())
                logger.info("Successfully refreshed access token")
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")

        return credentials

    def _load_credentials_from_file(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
        if not os.path.exists(token_file):
            return None

        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                return Credentials(
                    token=token_data['token'],
                    refresh_token=token_data.get('refresh_token'),
                    token_uri=token_data['token_uri'],
                    client_id=token_data['client_id'],
                    client_secret=token_data['client_secret'],
                    scopes=token_data['scopes']
                )
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.error(f"Error loading credentials from file: {e}")
            return None

    def _initialize_service(self) -> None:
        """Initialize the Google Calendar service with credentials."""
        if self.service:
            return

        self._credentials = self._load_credentials_from_env()
        if not self._credentials:
            self._credentials = self._load_credentials_from_file()

        if not self._credentials:
            raise RuntimeError("No valid Google Calendar credentials found in .env or token file")

        self.service = build('calendar', 'v3', credentials=self._credentials)

    def _parse_event_datetime(self, dt_str: str) -> tuple[datetime, bool]:
        """Parse event datetime string and determine if it's an all-day event."""
        if 'T' in dt_str:  # Has time component
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00')), False
        return datetime.fromisoformat(dt_str), True

    def _format_event(self, event: Dict[str, Any]) -> CalendarEvent:
        """Convert Google Calendar event to standardized format."""
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        start_dt, is_all_day = self._parse_event_datetime(start)
        end_dt, _ = self._parse_event_datetime(end)
        
        return CalendarEvent(
            title=event['summary'],
            start=start_dt,
            end=end_dt,
            is_all_day=is_all_day,
            color=event.get('colorId', 'blue')
        )

    def get_events(self, device_config: Any) -> List[CalendarEvent]:
        """
        Fetch events from Google Calendar API.
        
        Args:
            device_config: Configuration object containing environment variables
            
        Returns:
            List[CalendarEvent]: List of calendar events
            
        Raises:
            RuntimeError: If API call fails or credentials are invalid
        """
        try:
            self._initialize_service()
            
            # Get the current week's start and end
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Format dates for Google Calendar API
            time_min = week_start.isoformat() + 'Z'
            time_max = week_end.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [self._format_event(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            raise RuntimeError(f"Failed to fetch Google Calendar events: {str(e)}")
