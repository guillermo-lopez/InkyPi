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
- **Automatic Authentication**: Handles OAuth2 authentication for both services
- **Token Management**: Automatically refreshes expired tokens

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

# TickTick
TICKTICK_CLIENT_ID=your_ticktick_client_id
TICKTICK_CLIENT_SECRET=your_ticktick_client_secret
```

## Usage

The plugin will automatically:
1. Authenticate with both Google Calendar and TickTick
2. Fetch events and tasks for the current week
3. Display them in a weekly calendar view
4. Handle token refresh when needed

### First-time Authentication

On first run, the plugin will:
1. Open your default web browser
2. Prompt you to log in to Google Calendar and TickTick
3. Request necessary permissions
4. Save the authentication tokens for future use

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

1. **Token Expired**: The plugin will automatically attempt to refresh expired tokens
2. **Authentication Failed**: 
   - Check your Client ID and Client Secret
   - Ensure redirect URIs are correctly configured
   - Delete the token files in `~/.inkypi/` and try again

### Display Issues

1. **Text Cutoff**: Events are automatically truncated to fit the display
2. **Missing Events**: 
   - Check your Google Calendar and TickTick permissions
   - Verify that events are within the current week
   - Ensure events have valid start/end times

## Contributing

Feel free to submit issues and enhancement requests! 
