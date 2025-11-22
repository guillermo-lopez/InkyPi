"""Google Calendar service for fetching and formatting calendar events."""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import pytz
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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

        # Load additional calendar IDs (e.g., GOOGLE_CALENDAR_ID_HOLIDAYS)
        calendar_prefix = 'GOOGLE_CALENDAR_ID_'
        for key, value in os.environ.items():
            if key.startswith(calendar_prefix):
                calendar_name = key[len(calendar_prefix):].lower()
                self._calendar_ids[calendar_name] = value

        logger.info(f"Loaded {len(self._calendar_ids)} calendar IDs")

    def _log_token_state(self, context: str) -> None:
        """
        Log detailed token state for debugging authentication issues.

        Args:
            context: Description of when this logging is happening
        """
        if not self._credentials:
            logger.warning(f"[{context}] No credentials available")
            return

        import time
        from datetime import datetime, timezone

        logger.info(f"[{context}] TOKEN STATE:")
        logger.info(f"  Access Token: {self._credentials.token[:50]}..." if self._credentials.token else "  Access Token: None")
        logger.info(f"  Refresh Token: {'Present (' + self._credentials.refresh_token[:20] + '...)' if self._credentials.refresh_token else 'MISSING'}")
        logger.info(f"  Token Expiry: {self._credentials.expiry}")

        if self._credentials.expiry:
            # Make now timezone-aware to match credentials.expiry
            now = datetime.now(timezone.utc) if self._credentials.expiry.tzinfo else datetime.now()
            time_until_expiry = (self._credentials.expiry - now).total_seconds()
            logger.info(f"  Time until expiry: {time_until_expiry:.0f} seconds ({time_until_expiry/60:.1f} minutes)")
            logger.info(f"  Token expired: {self._credentials.expired}")

        logger.info(f"  Scopes: {', '.join(self._credentials.scopes) if self._credentials.scopes else 'None'}")

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
        """
        Initialize the Google Calendar service with credentials.

        Args:
            force_refresh: Force reload of credentials from disk
        """
        if self.service and not force_refresh:
            return

        logger.info("=" * 80)
        logger.info("INITIALIZING GOOGLE CALENDAR SERVICE")
        logger.info("=" * 80)
        logger.info(f"Force refresh: {force_refresh}")

        self._initialize_auth()

        # Get valid credentials (with automatic refresh if needed)
        self._credentials = self._auth.get_valid_credentials()
        if not self._credentials:
            raise RuntimeError(
                "No valid Google Calendar credentials found. "
                "Run: python3 src/plugins/task_calendar/auth/google_auth.py"
            )

        self._log_token_state("CREDENTIALS LOADED")

        # Set up a callback to save tokens after Google library auto-refreshes
        original_refresh = self._credentials.refresh

        def refresh_and_save(request):
            """Wrapper that saves tokens after refresh."""
            logger.info("=" * 80)
            logger.info("GOOGLE LIBRARY AUTO-REFRESHING TOKEN")
            logger.info("=" * 80)
            self._log_token_state("BEFORE AUTO-REFRESH")

            # Call the original refresh method
            original_refresh(request)

            self._log_token_state("AFTER AUTO-REFRESH")

            # Save the refreshed tokens to disk
            self._auth.save_tokens(self._credentials)
            logger.info("✓ Refreshed tokens saved to disk")
            logger.info("=" * 80)

        # Replace the refresh method with our wrapper
        self._credentials.refresh = refresh_and_save

        self.service = build('calendar', 'v3', credentials=self._credentials)
        logger.info("✓ Google Calendar service initialized successfully")
        logger.info("=" * 80)

    def _parse_event_datetime(self, dt_str: str) -> tuple[datetime, bool]:
        """
        Parse event datetime string and determine if it's an all-day event.

        Args:
            dt_str: ISO format datetime string

        Returns:
            Tuple of (datetime, is_all_day)
        """
        if 'T' in dt_str:  # Has time component
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, False

        # All-day event - use midnight UTC
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

    def _fetch_calendar_events(
        self,
        calendar_id: str,
        calendar_name: str,
        time_min: str,
        time_max: str
    ) -> List[CalendarEvent]:
        """
        Fetch events from a single calendar.

        Args:
            calendar_id: Google Calendar ID
            calendar_name: Friendly name for the calendar
            time_min: Start time in ISO format
            time_max: End time in ISO format

        Returns:
            List of CalendarEvent objects
        """
        logger.info("=" * 80)
        logger.info(f"FETCHING EVENTS FROM CALENDAR: {calendar_name}")
        logger.info("=" * 80)
        self._log_token_state(f"BEFORE API CALL [{calendar_name}]")

        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        logger.info(f"✓ API call successful for calendar: {calendar_name}")
        self._log_token_state(f"AFTER API CALL [{calendar_name}]")

        events = events_result.get('items', [])
        calendar_events = [self._format_event(event, calendar_name) for event in events]

        logger.info(f"Retrieved {len(calendar_events)} events from calendar: {calendar_name}")
        for event in calendar_events:
            logger.info(
                f"  Event: {event.title} - Start: {event.start} - "
                f"End: {event.end} - All Day: {event.is_all_day}"
            )
        logger.info("=" * 80)

        return calendar_events

    def _handle_auth_error(
        self,
        calendar_id: str,
        calendar_name: str,
        time_min: str,
        time_max: str,
        error: Exception
    ) -> List[CalendarEvent]:
        """
        Handle authentication errors by refreshing credentials and retrying.

        Args:
            calendar_id: Calendar ID that failed
            calendar_name: Calendar name that failed
            time_min: Start time for events
            time_max: End time for events
            error: Original error

        Returns:
            List of events if retry succeeds

        Raises:
            RuntimeError: If retry also fails
        """
        error_msg = str(error)
        logger.error("=" * 80)
        logger.error(f"AUTHENTICATION ERROR FOR CALENDAR: {calendar_name}")
        logger.error("=" * 80)
        logger.error(f"Error: {error}")
        logger.error(f"Error type: {type(error).__name__}")
        self._log_token_state("AT TIME OF AUTH ERROR")

        # Check if this is a refresh token error (cannot be automatically fixed)
        if "invalid_grant" in error_msg:
            logger.error("=" * 80)
            logger.error("REFRESH TOKEN IS INVALID OR EXPIRED")
            logger.error("=" * 80)
            logger.error("This cannot be fixed automatically. You must re-authenticate.")
            logger.error("")
            logger.error("On your development machine, run:")
            logger.error("  python3 src/plugins/task_calendar/auth/google_auth.py")
            logger.error("")
            logger.error("Then deploy the new token to your Pi:")
            logger.error("  scp ~/.inkypi/google_calendar_token.json inky-pi@inky-pi.local:~/.inkypi/")
            logger.error("")
            logger.error("The plugin will automatically pick up the new token on next refresh.")
            logger.error("=" * 80)
            raise RuntimeError(
                "Google Calendar refresh token is invalid or expired. "
                "Re-authentication required. See logs for instructions."
            )

        # For other auth errors, try to reload credentials from disk
        logger.warning("Attempting to reload credentials from disk and retry...")

        # Invalidate cached credentials
        self.service = None
        self._credentials = None

        try:
            # Re-initialize with fresh credentials from disk
            logger.info("Re-initializing service with fresh credentials...")
            self._initialize_service(force_refresh=True)

            # Retry the API call
            logger.info("Retrying API call...")
            calendar_events = self._fetch_calendar_events(
                calendar_id, calendar_name, time_min, time_max
            )

            logger.info("=" * 80)
            logger.info(f"✓ RECOVERY SUCCESSFUL: Retrieved {len(calendar_events)} events after credential refresh")
            logger.info("=" * 80)
            return calendar_events

        except Exception as retry_error:
            logger.error("=" * 80)
            logger.error("RECOVERY FAILED")
            logger.error("=" * 80)
            logger.error(f"Failed to fetch events after credential refresh: {retry_error}")
            logger.error(f"Retry error type: {type(retry_error).__name__}")
            logger.error("")
            logger.error("Re-authentication required. Run:")
            logger.error("  python3 src/plugins/task_calendar/auth/google_auth.py")
            logger.error("=" * 80)
            raise RuntimeError(f"Google Calendar authentication failed: {str(error)}")

    def get_events(self, device_config: Any) -> List[CalendarEvent]:
        """
        Fetch events from multiple Google Calendars for the current week.

        Args:
            device_config: Configuration object containing timezone settings

        Returns:
            List of CalendarEvent objects from all configured calendars

        Raises:
            RuntimeError: If API call fails or credentials are invalid
        """
        try:
            logger.info("")
            logger.info("=" * 80)
            logger.info("STARTING GOOGLE CALENDAR EVENT FETCH")
            logger.info("=" * 80)

            self._initialize_service()

            # Get current week boundaries (Sunday to Saturday) in device timezone
            device_tz = pytz.timezone(device_config.get_config("timezone", "US/Eastern"))
            now = datetime.now(device_tz)

            # Calculate week start (Sunday)
            days_since_sunday = (now.weekday() + 1) % 7
            week_start = now - timedelta(days=days_since_sunday)
            week_end = week_start + timedelta(days=6)

            # Convert to UTC for API
            time_min = week_start.astimezone(pytz.UTC).isoformat()
            time_max = week_end.astimezone(pytz.UTC).isoformat()

            logger.info(
                f"Fetching events from {time_min} to {time_max} "
                f"(EST: {week_start} to {week_end})"
            )
            logger.info(f"Configured calendars: {list(self._calendar_ids.keys())}")

            all_events = []

            # Fetch events from each calendar
            for calendar_name, calendar_id in self._calendar_ids.items():
                try:
                    calendar_events = self._fetch_calendar_events(
                        calendar_id, calendar_name, time_min, time_max
                    )
                    all_events.extend(calendar_events)

                except Exception as e:
                    error_msg = str(e)

                    # Check for authentication errors
                    if "invalid_grant" in error_msg or "Token has been expired or revoked" in error_msg:
                        # Try to recover by refreshing credentials
                        calendar_events = self._handle_auth_error(
                            calendar_id, calendar_name, time_min, time_max, e
                        )
                        all_events.extend(calendar_events)
                    else:
                        logger.error(f"Error fetching events from calendar {calendar_name}: {e}")
                        continue

            logger.info("=" * 80)
            logger.info(f"✓ FETCH COMPLETE: Retrieved {len(all_events)} total events from {len(self._calendar_ids)} calendars")
            self._log_token_state("FINAL TOKEN STATE")
            logger.info("=" * 80)
            logger.info("")

            return all_events

        except Exception as e:
            logger.error("=" * 80)
            logger.error("FATAL ERROR FETCHING GOOGLE CALENDAR EVENTS")
            logger.error("=" * 80)
            logger.error(f"Error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error("=" * 80)
            raise RuntimeError(f"Failed to fetch Google Calendar events: {str(e)}")
