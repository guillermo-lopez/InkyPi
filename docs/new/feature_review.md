# InkyPi v2 - Feature Review

All existing features confirmed for v2 rebuild. New features added for ESP32 architecture.

Legend: ✅ Keep | ⚠️ Modify | ❌ Remove | 🆕 New

---

## 1. Display & Image Settings

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Orientation | Horizontal/vertical display mode | ✅ | |
| Invert image | Rotate 180° for mounting flexibility | ✅ | |
| Brightness | Image brightness adjustment (0.0-2.0) | ✅ | |
| Contrast | Image contrast adjustment (0.0-2.0) | ✅ | |
| Saturation | Image color saturation (0.0-2.0) | ✅ | |
| Sharpness | Image sharpness adjustment (0.0-2.0) | ✅ | |
| Auto-resize | Crop/resize images to fit display | ✅ | |
| Keep-width mode | Stretch instead of center-crop (per plugin) | ✅ | |

---

## 2. Scheduling & Playlists

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Multiple playlists | Create named playlists with time ranges | ✅ | |
| Time-based activation | Playlist active during start_time to end_time | ✅ | |
| Plugin cycling | Rotate through plugins in playlist order | ✅ | |
| Interval refresh | Refresh every N minutes/hours/days | ✅ | |
| Scheduled refresh | Refresh at specific time daily (e.g., 8:00 AM) | ✅ | |
| Manual refresh | "Update Now" button for immediate display | ✅ | |
| Plugin cycle interval | Global default interval between plugin switches | ✅ | |
| Skip unchanged images | Don't refresh display if image hash unchanged | ✅ | |

---

## 3. Plugins

### 3.1 Clock Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Gradient clock face | Analog clock with conic gradient | ✅ | |
| Digital clock face | Digital display style | ✅ | |
| Divided clock face | Analog with divided design | ✅ | |
| Word clock face | Time displayed as words in grid | ✅ | |
| Custom colors | Primary/secondary color picker | ✅ | |
| Timezone support | Uses device timezone | ✅ | |

### 3.2 Weather Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Current conditions | Temperature, feels like, description | ✅ | |
| Location picker | Interactive map to set lat/long | ✅ | |
| Units | Imperial/metric/standard | ✅ | |
| Sunrise/sunset | Display times | ✅ | |
| Wind speed | Current wind conditions | ✅ | |
| Humidity | Current humidity % | ✅ | |
| Pressure | Atmospheric pressure | ✅ | |
| UV index | UV level display | ✅ | |
| Visibility | Current visibility | ✅ | |
| Air quality (AQI) | Air quality index | ✅ | |
| Hourly graph | 24-hour forecast graph | ✅ | |
| Daily forecast | 3/5/7 day forecast | ✅ | |
| Moon phase | Moon phase icons with illumination % | ✅ | |
| Last refresh time | Show when data was fetched | ✅ | |

### 3.3 AI Image Plugin (DALL-E)
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Text prompt | User enters image description | ✅ | |
| Model selection | DALL-E 2 or DALL-E 3 | ✅ | |
| Quality setting | HD or standard (DALL-E 3) | ✅ | |
| Auto-enhance prompt | GPT-4o improves prompt automatically | ✅ | |
| E-ink optimization | Prompt injection for better e-ink results | ✅ | |

### 3.4 AI Text Plugin (GPT)
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Custom title | Display title above generated text | ✅ | |
| Text prompt | What to generate (quote, fact, etc.) | ✅ | |
| Model selection | GPT-4o or GPT-4o-mini | ✅ | |
| Word limit | 70 word output limit | ✅ | |

### 3.5 APOD Plugin (NASA)
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Today's image | Astronomy Picture of the Day | ✅ | |
| Custom date | Specific date selection | ✅ | |
| Random mode | Random image from past 10 years | ✅ | |

### 3.6 Newspaper Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Newspaper selection | 1000+ newspapers worldwide | ✅ | |
| Location search | Filter by city/country | ✅ | |
| Auto date fallback | Tries today, yesterday, 2 days ago | ✅ | |

### 3.7 Image Upload Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Multi-file upload | Upload multiple images | ✅ | |
| Image carousel | Cycle through uploaded images | ✅ | |
| EXIF orientation | Auto-correct rotated JPEGs | ✅ | |
| Supported formats | PNG, JPG, JPEG, GIF, PDF | ✅ | |

### 3.8 Screenshot Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| URL input | Enter any website URL | ✅ | |
| Full page capture | Screenshot at display resolution | ✅ | |

### 3.9 Task Calendar Plugin
| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Google Calendar | OAuth2 integration | ✅ | |
| Multiple calendars | Show events from multiple calendars | ✅ | |
| TickTick tasks | Task integration | ✅ | |
| Weekly view | Sunday-Saturday display | ✅ | |
| Color coding | Events colored by calendar | ✅ | |
| Task priorities | Tasks colored by priority | ✅ | |
| Event duration | Variable height based on duration | ✅ | |
| Auto token refresh | Automatic OAuth token refresh | ✅ | |

---

## 4. Plugin System (Developer Features)

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Plugin auto-discovery | Scan plugins/ dir on startup | ✅ | |
| plugin-info.json | Metadata file for each plugin | ✅ | Renamed to plugin_meta.json |
| settings.html | Custom settings UI per plugin | ✅ | Django template partials |
| PIL rendering | Programmatic image generation | ✅ | |
| HTML/CSS rendering | Chromium-based template rendering | ✅ | |
| Plugin icons | Custom icon per plugin | ✅ | |
| Asset serving | Static files per plugin | ✅ | |
| Base template | Shared Jinja2 base for HTML plugins | ✅ | |
| Frame styles | Decorative frames around content | ✅ | |

---

## 5. Web UI

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Home page | Device status + plugin grid | ✅ | |
| Current image preview | Shows what's on display | ✅ | |
| Settings page | Device configuration | ✅ | |
| Plugin config page | Per-plugin settings form | ✅ | |
| Playlist page | Manage playlists and instances | ✅ | |
| Add to playlist modal | Schedule configuration | ✅ | |
| Response modals | Success/error feedback | ✅ | |
| Timezone selector | Autocomplete IANA timezones | ✅ | |
| Reboot/shutdown | System power controls | ✅ | |

---

## 6. System Features

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Systemd service | Runs as background service | ⚠️ | Replaced by Docker |
| Auto-start on boot | Service starts automatically | ⚠️ | Docker restart policy |
| Install script | One-command installation | ⚠️ | docker-compose up |
| Update script | Pull latest and restart | ⚠️ | docker-compose pull |
| Logging | journalctl integration | ⚠️ | Docker logs |
| Sentry errors | Error tracking in production | ✅ | |
| .env config | Environment variable secrets | ✅ | |

---

## 7. New Features for v2

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Database storage | PostgreSQL replaces device.json | 🆕 | Core architecture change |
| Celery task queue | Background job processing | 🆕 | Replaces background thread |
| ESP32 display transport | Push images to ESP32 over WiFi | 🆕 | HTTP or MQTT |
| Refresh history | Log of all past refreshes with images | 🆕 | |
| API key management UI | Add/edit keys in web interface | 🆕 | |
| Multiple display targets | Support multiple ESP32 displays | 🆕 | |
| Display health monitoring | Track ESP32 online/offline status | 🆕 | |
| Plugin enable/disable | Toggle plugins without deleting | 🆕 | |
| Mobile-friendly UI | Responsive design for phones | 🆕 | |
| Backup/restore | Export/import configuration | 🆕 | |
| Plugin settings validation | Schema-based validation | 🆕 | |
| Google OAuth in UI | Connect calendar via web UI flow | 🆕 | No CLI script needed |

---

## Summary

- **Total existing features:** 85+
- **Features kept:** All
- **Features modified:** 6 (system/deployment related)
- **New features:** 12

All plugins (9), all scheduling features, all image settings, and all web UI features carry over to v2. The main changes are architectural: Docker deployment, PostgreSQL database, Celery for background tasks, and ESP32 as the display transport layer instead of direct Pi GPIO.
