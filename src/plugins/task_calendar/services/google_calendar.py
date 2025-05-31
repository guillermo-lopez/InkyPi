from googleapiclient.discovery import build
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import os
import json
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class GoogleCalendar:
    def __init__(self):
        self.service = None

    def get_events(self, device_config):
        """
        Fetch events from Google Calendar API.
        
        Args:
            device_config: Configuration object containing environment variables
            
        Returns:
            list: List of events with start/end times and other metadata
            
        Raises:
            RuntimeError: If API call fails
        """
        try:
            # Get or build service
            if not self.service:
                # Try to load from .env first
                load_dotenv()
                access_token = os.getenv('GOOGLE_CALENDAR_ACCESS_TOKEN')
                client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
                client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
                refresh_token = os.getenv('GOOGLE_CALENDAR_REFRESH_TOKEN')
                
                if all([access_token, client_id, client_secret]):
                    credentials = Credentials(
                        token=access_token,
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=['https://www.googleapis.com/auth/calendar.readonly']
                    )
                    
                    # Try to refresh the token if we have a refresh token
                    if refresh_token:
                        try:
                            credentials.refresh(Request())
                            logger.info("Successfully refreshed access token")
                        except Exception as e:
                            logger.warning(f"Failed to refresh token: {e}")
                else:
                    # Fall back to token file
                    token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
                    if os.path.exists(token_file):
                        with open(token_file, 'r') as f:
                            token_data = json.load(f)
                            credentials = Credentials(
                                token=token_data['token'],
                                refresh_token=token_data.get('refresh_token'),
                                token_uri=token_data['token_uri'],
                                client_id=token_data['client_id'],
                                client_secret=token_data['client_secret'],
                                scopes=token_data['scopes']
                            )
                    else:
                        raise RuntimeError("No valid Google Calendar credentials found in .env or token file")
                
                self.service = build('calendar', 'v3', credentials=credentials)
            
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
            
            # Process events into a consistent format
            calendar_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Convert to datetime objects
                if 'T' in start:  # Has time component
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    is_all_day = False
                else:  # All-day event
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    is_all_day = True
                
                calendar_events.append({
                    'title': event['summary'],
                    'start': start_dt,
                    'end': end_dt,
                    'is_all_day': is_all_day,
                    'source': 'google',
                    'color': event.get('colorId', 'blue')  # Use Google Calendar color if available
                })
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            raise RuntimeError(f"Failed to fetch Google Calendar events: {str(e)}")
