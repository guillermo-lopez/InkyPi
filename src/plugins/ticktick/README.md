# TickTick Plugin for InkyPi

The TickTick plugin displays your tasks from the TickTick todo app on your InkyPi E-Ink display. It provides a weekly calendar view of your tasks, making it easy to see your schedule at a glance.

## Features

- **Weekly Calendar View**: 
  - Sunday to Saturday layout
  - Tasks displayed as colored rectangles
  - All-day tasks shown at the top of each day
  - Timed tasks listed below, sorted by time
- **Priority-based Colors**:
  - Black: Normal priority
  - Blue: Low priority
  - Orange: Medium priority
  - Red: High priority
- **Task Display**:
  - All-day tasks shown with bullet points
  - Timed tasks show start time (HH:MM)
  - Task titles truncated to fit display
  - Completed tasks shown in gray
- **Layout**:
  - Clear day headers with day name and date
  - Vertical grid lines separating days
  - Tasks stacked vertically within each day
  - Optimized for E-Ink display with appropriate contrast

## Setup

1. **Get TickTick Access Token**:
   - Log in to your TickTick account
   - Navigate to Settings > Developer
   - Generate a new access token

2. **Configure InkyPi**:
   - Open the InkyPi web interface
   - Go to Settings > Plugins > TickTick
   - Enter your TickTick access token
   - Save the configuration

## Usage

The plugin will automatically:
- Fetch your tasks from TickTick
- Display them in a weekly calendar format (Sunday to Saturday)
- Update when tasks are modified in TickTick
- Show task priorities and completion status
- Sort tasks by time within each day

## Technical Details

- Uses the TickTick Open API
- Supports timezone conversion
- Handles both timed and all-day tasks
- Optimized for E-Ink display with appropriate contrast
- Updates automatically with the InkyPi refresh cycle
- Calendar is centered on the display for optimal viewing

## Troubleshooting

If tasks aren't appearing:
1. Verify your access token is correct
2. Check your internet connection
3. Ensure you have tasks in your TickTick inbox
4. Check the InkyPi logs for any error messages

## Contributing

Feel free to contribute to this plugin by:
- Reporting bugs
- Suggesting new features
- Submitting pull requests
- Improving documentation

## License

This plugin is part of InkyPi and is distributed under the GPL 3.0 License. 
