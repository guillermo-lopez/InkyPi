# Calendar Plugin for InkyPi

A unified calendar plugin for InkyPi that displays both Google Calendar events and TickTick tasks in a weekly view on your e-ink display.

## Features

- **Unified Calendar View**: Combines Google Calendar events and TickTick tasks in a single weekly view
- **Color Coding**:
  - Google Calendar events: Blue
  - TickTick tasks: Color-coded by priority (Normal: Black, Low: Blue, Medium: Orange, High: Red)
  - Completed tasks: Gray
- **Time Display**: Shows events in 12-hour format (e.g., "9:30 AM")
- **All-day Events**: Displays both all-day events and timed events
- **Simple Authentication**: Uses environment variables or token file for authentication
- **No OAuth Flow**: No need for browser-based authentication after initial setup

## Directory Structure

```
task_calendar/
├── auth/                    # Authentication related code
├── services/               # Service implementations
│   ├── google_calendar.py  # Google Calendar service
│   └── ticktick.py        # TickTick service
├── task_calendar.py        # Main plugin implementation
├── debug_google_calendar.py # Debug script for Google Calendar
└── README.md              # This file
```

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

### Add missing packages
```
source /usr/local/inkypi/venv_inkypi/bin/activate
```
```
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-api-python-client
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-auth-oauthlib
sudo /usr/local/inkypi/venv_inkypi/bin/pip install google-auth-httplib2
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
# Google Calendar
GOOGLE_CALENDAR_CLIENT_ID=your_google_client_id
GOOGLE_CALENDAR_CLIENT_SECRET=your_google_client_secret
GOOGLE_CALENDAR_ACCESS_TOKEN=your_google_access_token

# TickTick
TICKTICK_CLIENT_ID=your_ticktick_client_id
TICKTICK_CLIENT_SECRET=your_ticktick_client_secret
```

### Getting Google Calendar Access Token

To get your Google Calendar access token:

1. Run the debug script once to get the token:
```bash
python3 src/plugins/task_calendar/debug_google_calendar.py
```

2. The script will:
   - Open your browser for authentication
   - Save the token to `~/.inkypi/google_calendar_token.json`
   - Print the token information

3. Copy the access token to your `.env` file

### Token File Location

The plugin will look for credentials in this order:
1. Environment variables in `.env` file
2. Token file at `~/.inkypi/google_calendar_token.json`

## Usage

The plugin will automatically:
1. Use credentials from `.env` file if available
2. Fall back to token file if environment variables are not set
3. Fetch events and tasks for the current week
4. Display them in a weekly calendar view

### Calendar Layout

- **Header**: Day names and dates
- **Columns**: One for each day of the week (Sunday to Saturday)
- **Events**:
  - All-day events shown first
  - Timed events shown with start time
  - Color-coded by source and priority
  - Limited to 25 characters for all-day events and 20 characters for timed events

## Troubleshooting

### Authentication Issues

1. **Invalid Credentials**: 
   - Check your Client ID and Client Secret in `.env`
   - Verify your access token is valid
   - Make sure all required environment variables are set

2. **Token File Issues**:
   - Check if token file exists at `~/.inkypi/google_calendar_token.json`
   - Verify token file contains valid JSON data
   - Delete token file if corrupted and run debug script again

### Display Issues

1. **Text Cutoff**: Events are automatically truncated to fit the display
2. **Missing Events**: 
   - Check your Google Calendar and TickTick permissions
   - Verify that events are within the current week
   - Ensure events have valid start/end times

## Contributing

Feel free to submit issues and enhancement requests! 
