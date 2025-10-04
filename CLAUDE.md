# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InkyPi is an open-source E-Ink display system powered by Raspberry Pi. It uses a Flask web server with a plugin-based architecture to display various content on Pimoroni Inky Impression displays. The system supports scheduled playlists and automatic display refresh.

## Architecture

### Core Components

- **Flask Web Application** (`src/inkypi.py`): Main entry point that initializes the web server, registers blueprints, and starts the background refresh task
- **Display Manager** (`src/display_manager.py`): Handles image rendering and display on the Inky e-ink hardware
- **Refresh Task** (`src/refresh_task.py`): Background thread that manages periodic display updates based on playlists and schedules
- **Config** (`src/config.py`): Central configuration manager that handles device settings, plugin metadata, and playlist management
- **Plugin Registry** (`src/plugins/plugin_registry.py`): Dynamically loads plugins from the `plugins/` directory at startup

### Plugin System

All plugins inherit from `BasePlugin` (`src/plugins/base_plugin/base_plugin.py`) and must implement:
- `generate_image(settings, device_config)`: Returns a PIL Image object to display
- Plugin metadata in `plugin-info.json` with: `display_name`, `id`, `class`
- Optional `settings.html` for web UI configuration
- Optional `generate_settings_template()` to pass variables to the settings template

Plugins can generate images either:
1. **Programmatically** using PIL/Pillow
2. **From HTML/CSS** using `render_image()` method which renders Jinja2 templates via headless Chromium

### Refresh System

The refresh system has two modes:
- **Playlist Refresh**: Cycles through plugin instances in a playlist based on schedules and intervals
- **Manual Refresh**: Immediate update triggered from the web UI

Plugin instances can have individual refresh intervals. The `RefreshTask` determines which plugin to refresh based on:
- Active playlist schedule
- Plugin cycle interval
- Plugin instance refresh interval
- Last refresh timestamp

## Development Commands

### Service Management
```bash
# Restart the InkyPi service
sudo systemctl restart inkypi.service

# View service logs
journalctl -u inkypi -n 100 -f
```

### Installation & Updates
```bash
# Install InkyPi
sudo bash install/install.sh

# Update InkyPi
sudo bash install/update.sh

# Uninstall InkyPi
sudo bash install/uninstall.sh
```

### Plugin Testing
```bash
# Test a plugin across all display sizes and orientations
python scripts/test_plugin.py
```

Edit the script to change `plugin_id` and `plugin_settings` before running.

### Virtual Environment
Production uses: `/usr/local/inkypi/venv_inkypi/bin/python`

## Key Files & Directories

- `src/inkypi.py`: Main Flask application
- `src/config/device.json`: Device configuration and playlist state (auto-generated)
- `src/plugins/`: Plugin directory (each plugin in its own subfolder)
- `src/blueprints/`: Flask route handlers for web UI
- `src/utils/`: Utility functions for images, time, and app operations
- `install/`: Installation, update, and service scripts

## Plugin Development

See `docs/building_plugins.md` for the full plugin development guide.

### Quick Reference
1. Create directory: `src/plugins/{plugin_id}/`
2. Add Python file: `{plugin_id}.py` with class extending `BasePlugin`
3. Implement `generate_image(settings, device_config)` method
4. Create `plugin-info.json` with metadata
5. Optional: Add `settings.html`, `icon.png`, and `render/` directory for HTML/CSS templates
6. Restart service to load plugin

### Template Rendering
Plugins using `render_image()` should:
- Place HTML/CSS files in `render/` subdirectory
- Extend `plugin.html` base template
- Pass `plugin_settings` key in template_params to enable style options (background, margin, frames)
- Use Jinja2 templating with variables from `template_params`

## Important Notes

- All plugins are loaded at startup based on `plugin-info.json` presence
- Device resolution is auto-detected from the Inky display on first run
- Images are automatically resized and rotated based on device orientation settings
- Plugin instances store their state in `device.json` and images in `src/static/images/plugins/`
- The system uses a background thread for refreshes to avoid blocking the web UI
- Sentry error tracking is enabled in production

## Task Calendar Plugin

The `task_calendar` plugin is a custom addition that integrates Google Calendar and TickTick:
- Located in `src/plugins/task_calendar/`
- Uses Google Calendar API with OAuth2 token refresh
- Displays weekly calendar view (Sunday-Saturday)
- Color-codes events by calendar type and tasks by priority
- See `src/plugins/task_calendar/README.md` for detailed documentation
