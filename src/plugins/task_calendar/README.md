# Calendar Plugin for InkyPi

A unified calendar plugin for InkyPi that displays both Google Calendar events and TickTick tasks in a weekly view on your e-ink display.

## Features

- **Unified Calendar View**: Combines Google Calendar events and TickTick tasks in a single weekly view
- **Color Coding**:
  - Google Calendar events: Color-coded by calendar type
    - Primary: Red
    - Events Available: Purple
    - Holidays: Green
    - Birthdays: Orange
    - Partiful: Green
    - Other Google: Blue
  - TickTick tasks: Color-coded by priority
    - Normal: Blue
    - Low: Black
    - Medium: Orange
    - High: Pink
  - Completed tasks: Gray
- **Time Display**: Shows events in 12-hour format (e.g., "9:30 AM")
- **Event Duration Visualization**:
  - All-day events: Standard height
  - Short events (< 3 hours): Height proportional to duration
    - 30 minutes = 1x height
    - 1 hour = 2x height
    - 1.5 hours = 3x height
    - 2 hours = 4x height
    - 2.5 hours = 5x height
    - 3 hours = 6x height
  - Long events (≥ 3 hours): Standard height
- **Multi-day Events**: Shows as separate boxes for each day the event spans
- **Simple Authentication**: Uses JSON token file with automatic refresh
- **No OAuth Flow**: No need for browser-based authentication after initial setup

## Directory Structure

```
task_calendar/
├── auth/                    # Authentication related code
├── services/               # Service implementations
│   ├── google_calendar.py  # Google Calendar service
│   └── ticktick.py        # TickTick service
├── ui/                     # UI components
│   ├── layout.py          # Calendar layout calculations
│   ├── renderer.py        # Calendar rendering logic
│   └── styles.py          # Visual styling constants
├── task_calendar.py        # Main plugin implementation
├── debug_google_calendar.py # Debug script for Google Calendar
└── README.md              # This file
```

## Component Overview

### UI Components
- **layout.py**: Handles calendar layout calculations, including:
  - Week start date calculation (Sunday to Saturday)
  - Day index computation
  - Item height calculations based on duration
  - Calendar dimensions and positioning

- **renderer.py**: Manages all drawing operations:
  - Calendar structure (headers, grid lines)
  - Event and task rendering with variable heights
  - Multi-day event handling
  - Font management
  - Timestamp display

- **styles.py**: Contains all visual constants:
  - Color definitions for priorities and events
  - Layout dimensions and spacing
  - Font sizes
  - Text length limits

### Services
- **google_calendar.py**: Handles Google Calendar API integration
  - Supports multiple calendars
  - Converts all times to EST
  - Handles all-day and multi-day events
- **ticktick.py**: Manages TickTick API integration
  - Supports task priorities
  - Handles completed tasks
  - Converts all times to EST

## Setup

### Prerequisites

1. Python 3.7 or higher
2. Required Python packages (install using `pip install -r requirements.txt`):
   - google-auth-oauthlib
   - google-auth-httplib2
   - google-api-python-client
   - requests
   - python-dotenv
   - Pillow
   - pytz

### Autheticate
```
source /Users/glopez/projects/code/InkyPi/.venv/bin/activate
```
```
python3 google_auth.py
``` 
### Add missing packages
```
source /usr/local/inkypi/venv_inkypi/bin/activate
```
```
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-api-python-client
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-auth-oauthlib
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-auth-httplib2
sudo /usr/local/inkypi/venv_inkypi/bin/pip install pytz
```
```
deactivate
```
```
sudo systemctl restart inkypi.service
```

### Google Calendar Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Add `http://localhost:8000/callback` as an authorized redirect URI
5. Note down your Client ID and Client Secret

### TickTick Setup

1. Go to the [TickTick Developer Portal](https://ticktick.com/developer)
2. Create a new application
3. Add `http://localhost:8000/callback` as a redirect URI
4. Note down your Client ID and Client Secret

### Environment Variables

Create a `.env` file in your project root with the following variables:

```env
# Google Calendar (Client credentials only - tokens are stored in JSON file)
GOOGLE_CALENDAR_CLIENT_ID=your_google_client_id
GOOGLE_CALENDAR_CLIENT_SECRET=your_google_client_secret
GOOGLE_CALENDAR_TOKEN_FILE=~/.inkypi/google_calendar_token.json
GOOGLE_CALENDAR_ID=your_primary_calendar_id
GOOGLE_CALENDAR_ID_EVENTS_AVAILABLE=your_events_calendar_id
GOOGLE_CALENDAR_ID_HOLIDAYS=your_holidays_calendar_id
GOOGLE_CALENDAR_ID_BIRTHDAYS=your_birthdays_calendar_id
GOOGLE_CALENDAR_ID_PARTIFUL=your_partiful_calendar_id
GOOGLE_CALENDAR_ID_OTHER_GOOGLE=your_other_calendar_id

# TickTick
TICKTICK_ACCESS_TOKEN=your_ticktick_access_token
```

### Getting Google Calendar Access Token

To get your Google Calendar access token:

1. Run the authentication script once to set up credentials:
```bash
python3 src/plugins/task_calendar/auth/google_auth.py
```

2. The script will:
   - Open your browser for authentication
   - Save the tokens to `~/.inkypi/google_calendar_token.json`
   - Print the token information

3. The plugin will automatically refresh tokens when they expire

#### How Token Refresh Works

The plugin uses a sophisticated token refresh mechanism to maintain long-term operation:

1. **Access Tokens**: Expire after ~1 hour
2. **Refresh Tokens**: Used to obtain new access tokens without re-authentication
3. **Automatic Refresh**: Google's library automatically refreshes access tokens during API calls
4. **Token Persistence**: The plugin intercepts all auto-refresh operations and saves updated tokens to disk

**What This Means:**
- Once authenticated, the plugin should work indefinitely without manual re-authentication
- Every ~50-55 minutes, you'll see log messages showing token refresh:
  ```
  Google library auto-refreshing token...
  ✓ Auto-refresh successful!
  ✓ Refreshed tokens saved to disk
  ```
- Refresh tokens themselves expire after several months of inactivity
- Only when the refresh token expires will manual re-authentication be required

### Testing Authentication

To test if your authentication is working correctly:

```bash
python3 src/plugins/task_calendar/test_auth.py
```

This script will check if your token file exists and if the credentials are valid.

### Re-authentication

Re-authentication is rarely needed thanks to automatic token refresh. You'll only need to re-authenticate if:

1. **Refresh Token Expired**: The refresh token itself has expired (after several months of inactivity)
2. **Token Revoked**: You manually revoked the app's access in Google Account settings
3. **Invalid Grant Error**: You see persistent `invalid_grant` errors in the logs

To re-authenticate:

```bash
python3 src/plugins/task_calendar/auth/google_auth.py
```

This will automatically handle re-authentication and overwrite the old tokens.

**On Raspberry Pi:**
After re-authenticating on your development machine, deploy the new token file:
```bash
scp ~/.inkypi/google_calendar_token.json inky-pi@inky-pi.local:~/.inkypi/
```
The plugin will automatically pick up the new token on the next refresh (no service restart needed).

### Token File Location

The plugin stores all Google Calendar tokens in a JSON file. The default location is:
- `~/.inkypi/google_calendar_token.json`

You can customize the token file location by setting the `GOOGLE_CALENDAR_TOKEN_FILE` environment variable in your `.env` file.

The plugin will automatically refresh expired tokens using the refresh token.

## Usage

The plugin will automatically:
1. Load Google Calendar credentials from the JSON token file
2. Refresh expired tokens automatically using the refresh token
3. Fetch events and tasks for the current week (Sunday to Saturday)
4. Display them in a weekly calendar view with proper timezone handling (EST)

### Calendar Layout

- **Header**: Day names and dates
- **Columns**: One for each day of the week (Sunday to Saturday)
- **Events**:
  - All-day events shown first
  - Timed events shown with start time
  - Height varies based on duration for short events
  - Multi-day events shown as separate boxes for each day
  - Color-coded by source and priority
  - Limited to 25 characters for all-day events and 20 characters for timed events

## Common Commands
1. Update Server Code and restart server
```
scp -r src/plugins/task_calendar inky-pi@inky-pi.local:InkyPi/src/plugins/ && ssh inky-pi@inky-pi.local "sudo systemctl restart inkypi.service"
```
2. View Server Logs
```
journalctl -u inkypi -n 100 -f
```
3. Service Restart
```
sudo systemctl restart inkypi.service
```

## Troubleshooting

### Authentication Issues

1. **Invalid Credentials**: 
   - Check your Client ID and Client Secret in `.env`
   - Verify the token file exists at `~/.inkypi/google_calendar_token.json`
   - Make sure all required environment variables are set

2. **Token File Issues**:
   - Check if token file exists at `~/.inkypi/google_calendar_token.json`
   - Verify token file contains valid JSON data
   - Delete token file if corrupted and run authentication script again

3. **Token Refresh Issues**:
   - The plugin automatically refreshes expired access tokens every ~50-55 minutes
   - You should see refresh log messages in the service logs (`journalctl -u inkypi -f`)
   - If you see persistent `invalid_grant` errors, the refresh token has expired and you need to re-authenticate:
     ```bash
     python3 src/plugins/task_calendar/auth/google_auth.py
     # Then deploy to Pi:
     scp ~/.inkypi/google_calendar_token.json inky-pi@inky-pi.local:~/.inkypi/
     ```
   - Check that your Google Calendar app has the necessary permissions

### Display Issues

1. **Text Cutoff**: Events are automatically truncated to fit the display
2. **Missing Events**: 
   - Check your Google Calendar and TickTick permissions
   - Verify that events are within the current week
   - Ensure events have valid start/end times
   - Check timezone settings (should be EST)

### Timezone Issues

1. **Wrong Times**: 
   - Verify that your device's timezone is set correctly
   - Check that the events are being converted to EST
   - Ensure the week boundaries are correct (Sunday to Saturday)

## Contributing

Feel free to submit issues and enhancement requests! 
