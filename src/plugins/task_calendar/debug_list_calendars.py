"""Script to list all available Google Calendars and their IDs."""

from googleapiclient.discovery import build
import logging
from dotenv import load_dotenv
import os
from auth.google_auth import authenticate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """List all available calendars and their IDs."""
    try:
        # Authenticate using GoogleCalendarAuth
        auth = authenticate()
        if not auth:
            logger.error("Failed to authenticate with Google Calendar")
            return
        
        # Get credentials from auth
        credentials = auth.load_tokens()
        if not credentials:
            logger.error("No valid credentials found")
            return
        
        # Build the service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Get calendar list
        calendar_list = service.calendarList().list().execute()
        
        print("\nAvailable Google Calendars:")
        print("=" * 80)
        
        for calendar in calendar_list.get('items', []):
            calendar_id = calendar['id']
            calendar_name = calendar['summary']
            calendar_description = calendar.get('description', 'No description')
            calendar_color = calendar.get('backgroundColor', 'No color')
            
            print(f"\nCalendar Name: {calendar_name}")
            print(f"Calendar ID: {calendar_id}")
            print(f"Description: {calendar_description}")
            print(f"Color: {calendar_color}")
            print("-" * 80)
            
            # Print the environment variable format
            if calendar_id == 'primary':
                print("Add to .env as:")
                print(f"GOOGLE_CALENDAR_ID={calendar_id}")
            else:
                # Convert calendar name to lowercase and replace spaces with underscores
                env_name = calendar_name.lower().replace(' ', '_')
                print("Add to .env as:")
                print(f"GOOGLE_CALENDAR_ID_{env_name}={calendar_id}")
        
        print("\nTo use these calendars, add the appropriate lines to your .env file.")
        print("Example:")
        print("GOOGLE_CALENDAR_ID=primary")
        print("GOOGLE_CALENDAR_ID_work=work_calendar_id@group.calendar.google.com")
        print("GOOGLE_CALENDAR_ID_personal=personal_calendar_id@group.calendar.google.com")
        
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        raise

if __name__ == '__main__':
    main() 
