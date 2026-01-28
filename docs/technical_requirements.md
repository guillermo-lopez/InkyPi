# InkyPi v2 - Technical Requirements Document

## 1. Project Overview

Rebuild InkyPi as a modern, database-backed Python web application running in Docker on a Raspberry Pi. The server generates images and transmits them to an ESP32 microcontroller connected to an e-ink display over WiFi.

### Architecture Change Summary

| Aspect | Current (v1) | New (v2) |
|--------|-------------|----------|
| Server | Flask on bare metal | Django in Docker |
| Database | JSON file (`device.json`) | PostgreSQL |
| Task Queue | Background thread | Celery + Redis |
| Display Driver | Direct Inky library (Pi GPIO) | HTTP/MQTT push to ESP32 |
| Config | Flat JSON file | Database models |
| Deployment | Systemd service + install script | Docker Compose |
| Plugin Loading | Filesystem scan at startup | Database-registered, hot-reloadable |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Raspberry Pi (Docker)                  │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐  │
│  │  Django   │  │  Celery   │  │ Redis  │  │ Postgres │  │
│  │  Web App  │  │  Worker   │  │        │  │          │  │
│  │  :8000    │  │  + Beat   │  │  :6379 │  │  :5432   │  │
│  └────┬─────┘  └────┬─────┘  └────────┘  └──────────┘  │
│       │              │                                   │
│       └──────┬───────┘                                   │
│              │ Generate Image (PIL / Chromium)            │
│              ▼                                           │
│       ┌─────────────┐                                    │
│       │ Image Output │── HTTP/MQTT ──┐                   │
│       │  Service     │               │                   │
│       └─────────────┘               │                   │
└─────────────────────────────────────│───────────────────┘
                                      │ WiFi
                                      ▼
                              ┌──────────────┐
                              │    ESP32      │
                              │  + E-Ink      │
                              │  Display      │
                              └──────────────┘
```

### Services (Docker Compose)

| Service | Image / Build | Purpose |
|---------|--------------|---------|
| `app` | Custom (Python 3.12) | Django web server |
| `worker` | Same image | Celery worker for image generation |
| `beat` | Same image | Celery Beat for scheduled refreshes |
| `db` | `postgres:16` | Primary database |
| `redis` | `redis:7-alpine` | Message broker + cache |

---

## 3. Technology Stack

### Backend
- **Language:** Python 3.12
- **Framework:** Django 5.x
- **Task Queue:** Celery 5.x with Redis broker
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Image Processing:** Pillow (PIL), NumPy
- **HTML Rendering:** Chromium headless shell
- **API Style:** Django REST Framework (optional) or Django views returning JSON

### Frontend (Web UI)
- **Templating:** Django templates (Jinja2-compatible)
- **CSS:** Tailwind CSS or plain CSS (match current simplicity)
- **JavaScript:** Vanilla JS (minimal, for modals and form interactions)
- **Map Widget:** Leaflet.js (for weather location picker)

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Process Manager:** Docker Compose (replaces systemd)
- **Environment Config:** `.env` file with `django-environ`

---

## 4. Database Schema

### 4.1 Device Configuration

```
devices
├── id (PK)
├── name (varchar, default "InkyPi")
├── orientation (enum: horizontal, vertical)
├── inverted_image (boolean, default false)
├── timezone (varchar, IANA timezone)
├── resolution_width (integer)
├── resolution_height (integer)
├── scheduler_sleep_seconds (integer, default 60)
├── plugin_cycle_interval_seconds (integer, default 3600)
├── created_at (timestamp)
└── updated_at (timestamp)

device_image_settings
├── id (PK)
├── device_id (FK -> devices)
├── saturation (float, default 1.0)
├── brightness (float, default 1.0)
├── sharpness (float, default 1.0)
├── contrast (float, default 1.0)
└── updated_at (timestamp)
```

### 4.2 ESP32 Display Targets

```
display_targets
├── id (PK)
├── device_id (FK -> devices)
├── name (varchar)
├── transport_type (enum: http, mqtt)
├── endpoint_url (varchar, nullable — for HTTP)
├── mqtt_topic (varchar, nullable — for MQTT)
├── resolution_width (integer)
├── resolution_height (integer)
├── color_mode (enum: bw, bwr, bwry, 7color)
├── last_seen_at (timestamp, nullable)
├── is_active (boolean, default true)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### 4.3 Plugins

```
plugins
├── id (PK)
├── plugin_id (varchar, unique — e.g. "clock", "weather")
├── display_name (varchar)
├── class_name (varchar)
├── icon_path (varchar, nullable)
├── is_enabled (boolean, default true)
├── image_settings (jsonb, nullable — e.g. ["keep-width"])
├── requires_api_key (varchar, nullable — env var name)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### 4.4 Playlists

```
playlists
├── id (PK)
├── device_id (FK -> devices)
├── name (varchar)
├── start_time (time — HH:MM)
├── end_time (time — HH:MM)
├── is_active (boolean, default true)
├── current_plugin_index (integer, default 0)
├── sort_order (integer, default 0)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### 4.5 Plugin Instances (plugins assigned to playlists)

```
plugin_instances
├── id (PK)
├── playlist_id (FK -> playlists)
├── plugin_id (FK -> plugins)
├── instance_name (varchar)
├── settings (jsonb — plugin-specific config)
├── refresh_type (enum: interval, scheduled)
├── refresh_interval_seconds (integer, nullable)
├── refresh_scheduled_time (time, nullable — HH:MM)
├── latest_refresh_at (timestamp, nullable)
├── cached_image_path (varchar, nullable)
├── sort_order (integer, default 0)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### 4.6 Refresh History (new — replaces ephemeral refresh_info)

```
refresh_logs
├── id (PK)
├── device_id (FK -> devices)
├── plugin_instance_id (FK -> plugin_instances, nullable)
├── plugin_id (FK -> plugins)
├── refresh_type (enum: playlist, manual)
├── playlist_name (varchar, nullable)
├── image_hash (varchar(64))
├── image_path (varchar)
├── display_skipped (boolean — true if hash unchanged)
├── error_message (text, nullable)
├── duration_ms (integer — generation time)
├── created_at (timestamp)
└── display_target_id (FK -> display_targets, nullable)
```

### 4.7 API Keys / Credentials

```
api_credentials
├── id (PK)
├── service_name (varchar — e.g. "openweathermap", "openai", "google_calendar")
├── key_name (varchar — e.g. "OPEN_WEATHER_MAP_SECRET")
├── key_value (text, encrypted)
├── metadata (jsonb, nullable — e.g. OAuth tokens, expiry)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### 4.8 Uploaded Files

```
uploaded_files
├── id (PK)
├── original_filename (varchar)
├── stored_path (varchar)
├── file_type (varchar — e.g. "image/png")
├── file_size_bytes (integer)
├── created_at (timestamp)
└── updated_at (timestamp)

plugin_instance_files (M2M)
├── id (PK)
├── plugin_instance_id (FK -> plugin_instances)
├── uploaded_file_id (FK -> uploaded_files)
└── sort_order (integer)
```

---

## 5. Plugin System

### 5.1 Plugin Structure (on disk)

Each plugin lives in its own directory under `plugins/`:

```
plugins/
└── weather/
    ├── plugin.py              # Plugin class extending BasePlugin
    ├── plugin_meta.json       # Metadata (replaces plugin-info.json)
    ├── settings_form.html     # Django template partial for settings UI
    ├── icon.png               # Plugin icon
    ├── render/                # HTML/CSS templates for Chromium rendering
    │   ├── weather.html
    │   └── weather.css
    └── assets/                # Static files (icons, images, fonts)
```

### 5.2 Plugin Metadata (`plugin_meta.json`)

```json
{
  "id": "weather",
  "display_name": "Weather",
  "class": "Weather",
  "version": "1.0.0",
  "description": "Display current weather and forecast",
  "author": "InkyPi",
  "requires_api_key": "OPEN_WEATHER_MAP_SECRET",
  "image_settings": [],
  "settings_schema": {
    "latitude": {"type": "float", "label": "Latitude", "required": true},
    "longitude": {"type": "float", "label": "Longitude", "required": true},
    "units": {"type": "select", "options": ["imperial", "metric", "standard"], "default": "imperial"}
  }
}
```

### 5.3 BasePlugin Interface

```python
class BasePlugin(ABC):
    """Abstract base class for all plugins."""

    def __init__(self, config: dict, device: Device):
        self.config = config
        self.device = device

    @abstractmethod
    def generate_image(self, settings: dict, device_config: Device) -> Image:
        """Generate a PIL Image for the display. Required."""
        ...

    def generate_settings_context(self) -> dict:
        """Return extra context variables for the settings form template. Optional."""
        return {}

    def render_html(self, dimensions: tuple, template: str, css: str = None, context: dict = {}) -> Image:
        """Render an HTML/CSS template to a PIL Image via headless Chromium."""
        ...

    def get_plugin_dir(self, subpath: str = None) -> str:
        """Get absolute path to plugin directory or subdirectory."""
        ...

    def get_asset_url(self, filename: str) -> str:
        """Get URL for serving a plugin static asset."""
        ...
```

### 5.4 Plugin Registration

- On startup, scan `plugins/` directory for `plugin_meta.json` files
- Sync discovered plugins with the `plugins` database table
- Mark plugins not found on disk as disabled
- New plugins on disk get auto-registered as enabled

### 5.5 Existing Plugins to Port

| Plugin ID | Rendering | External API | Priority |
|-----------|-----------|-------------|----------|
| `clock` | PIL (programmatic) | None | High |
| `weather` | HTML/CSS (Chromium) | OpenWeatherMap | High |
| `ai_image` | PIL (remote image) | OpenAI DALL-E | Medium |
| `ai_text` | HTML/CSS (Chromium) | OpenAI GPT | Medium |
| `apod` | PIL (remote image) | NASA APOD | Medium |
| `newspaper` | PIL (remote image) | Freedom Forum CDN | Medium |
| `image_upload` | PIL (local file) | None | High |
| `screenshot` | Chromium screenshot | None | Low |
| `task_calendar` | PIL (programmatic) | Google Calendar, TickTick | High |

---

## 6. Scheduling & Refresh System

### 6.1 Celery Beat Schedules

Replace the single background thread with Celery Beat periodic tasks:

| Task | Schedule | Purpose |
|------|----------|---------|
| `check_playlist_refresh` | Every 60 seconds | Check if any plugin instance needs refresh |
| `cleanup_old_images` | Daily | Remove orphaned cached images |
| `cleanup_refresh_logs` | Weekly | Prune old refresh log entries |

### 6.2 Refresh Logic

**Playlist Refresh Flow:**
1. `check_playlist_refresh` task runs every 60 seconds
2. For each active device:
   a. Determine the active playlist based on current time vs playlist time ranges
   b. Get the next plugin instance in rotation (`current_plugin_index`)
   c. Check if that instance needs refresh:
      - **Interval:** `now - latest_refresh_at >= refresh_interval_seconds`
      - **Scheduled:** Current time >= scheduled time AND hasn't refreshed today
   d. If refresh needed:
      - Dispatch `generate_and_display` Celery task
      - Increment `current_plugin_index` (wrap around)
   e. If not needed: check next instance in rotation

**`generate_and_display` Task:**
1. Load plugin class and instantiate
2. Call `plugin.generate_image(instance.settings, device)`
3. Compute image hash
4. If hash differs from last display OR force refresh:
   a. Apply image enhancements (brightness, contrast, saturation, sharpness)
   b. Resize/rotate for target display orientation
   c. Save to disk cache
   d. Push image to ESP32 display target(s)
5. Log refresh to `refresh_logs` table
6. Update `plugin_instance.latest_refresh_at`

**Manual Refresh:**
1. User clicks "Update Now" in web UI
2. Django view dispatches `generate_and_display` task with `refresh_type=manual`
3. Task runs immediately (Celery priority queue or `apply_async`)
4. Returns result to user (success/error)

### 6.3 Playlist Scheduling Rules

- Playlists have `start_time` and `end_time` (HH:MM format, 24-hour)
- Multiple playlists can be active at the same time
- Conflict resolution: shortest time range wins (most specific schedule takes priority)
- Default playlist: `00:00` to `24:00` (always active as fallback)
- Plugin instances within a playlist cycle in order by `sort_order`

---

## 7. ESP32 Display Transport

### 7.1 Transport Protocols

Support two transport methods for pushing images to ESP32:

**HTTP Push:**
- Server sends POST request to ESP32's HTTP endpoint
- Payload: raw bitmap data (pre-processed for e-ink color palette)
- Endpoint: `http://<esp32_ip>:<port>/display`
- Content-Type: `application/octet-stream` or `image/bmp`
- ESP32 runs a minimal HTTP server (Arduino/ESP-IDF)

**MQTT (Alternative):**
- Server publishes image data to an MQTT topic
- ESP32 subscribes to its topic
- Broker: Mosquitto (add to Docker Compose if needed)
- Topic format: `inkypi/displays/<display_id>/image`
- Chunked transfer for large images

### 7.2 Image Pre-Processing for ESP32

Before transmission, the server must:
1. Resize image to target display resolution
2. Apply orientation rotation
3. Apply image enhancements
4. Convert color palette to match display type:
   - **B/W:** 1-bit dithering (Floyd-Steinberg)
   - **B/W/R:** Map to 3-color palette
   - **B/W/R/Y:** Map to 4-color palette
   - **7-color:** Map to 7-color palette (Inky Impression)
5. Pack pixel data into the format the ESP32/display driver expects
6. Compress if needed (optional gzip for HTTP)

### 7.3 ESP32 Registration & Discovery

- ESP32 announces itself via mDNS or connects to a known server endpoint
- Server stores ESP32 targets in `display_targets` table
- Health check: periodic ping or last-seen tracking
- Manual registration via web UI as fallback

### 7.4 ESP32 Firmware (Out of Scope — Notes Only)

The ESP32 firmware is a separate project but should:
- Connect to WiFi (credentials via BLE provisioning or hardcoded)
- Run an HTTP server to receive image data OR subscribe to MQTT topic
- Drive the e-ink display using the appropriate driver (GxEPD2 library for Arduino)
- Support deep sleep between updates for power efficiency
- Report display resolution and color mode to server on registration

---

## 8. Web UI Requirements

### 8.1 Pages

**Home Page (`/`)**
- Device name and status (last refresh time, active playlist)
- Current displayed image (live preview)
- Plugin grid with icons — click to configure
- Quick actions: manual refresh, pause/resume playlist

**Device Settings (`/settings`)**
- Device name
- Orientation (horizontal/vertical)
- Invert image toggle
- Timezone selector (IANA timezones with autocomplete)
- Default plugin cycle interval (number + unit)
- Image enhancement sliders (saturation, brightness, sharpness, contrast — range 0.0 to 2.0)
- System actions: reboot, shutdown

**Display Targets (`/displays`)**  *(new)*
- List of registered ESP32 displays
- For each: name, IP, resolution, color mode, last seen, status
- Add/edit/remove display targets
- Test button (send test image)

**Plugin Configuration (`/plugin/<plugin_id>`)**
- Dynamic settings form (loaded from plugin's `settings_form.html`)
- Two action modes:
  1. **Update Now** — generate and display immediately
  2. **Add to Playlist** — open modal to select playlist, name instance, set refresh schedule
- When editing existing instance: pre-populate form with saved settings

**Playlist Management (`/playlists`)**
- List of all playlists with time ranges
- For each playlist: ordered list of plugin instances
- CRUD operations: create, edit, delete playlists
- Per instance: display now, edit settings, remove, reorder (drag-and-drop or arrows)
- Create playlist modal: name, start time, end time

**Refresh History (`/history`)**  *(new)*
- Paginated log of all refresh events
- Columns: timestamp, plugin, playlist, type (manual/scheduled), duration, status, image thumbnail
- Filter by plugin, playlist, date range
- Click to view full-size generated image

**API Keys (`/settings/api-keys`)**  *(new)*
- Manage API keys for external services
- Add/edit/delete keys
- Fields: service name, key name, key value (masked)
- Status indicator (valid/invalid based on last use)

### 8.2 API Endpoints

All data-mutating endpoints return JSON. Pages return HTML.

**Device:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Home page |
| GET | `/settings` | Settings page |
| POST | `/api/settings` | Update device settings |
| POST | `/api/shutdown` | Reboot or shutdown |

**Displays:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/displays` | Display targets page |
| GET | `/api/displays` | List all display targets |
| POST | `/api/displays` | Register new display target |
| PUT | `/api/displays/<id>` | Update display target |
| DELETE | `/api/displays/<id>` | Remove display target |
| POST | `/api/displays/<id>/test` | Send test image |

**Plugins:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/plugin/<plugin_id>` | Plugin settings page |
| GET | `/api/plugins` | List all plugins |
| POST | `/api/plugins/refresh` | Manual refresh (generate & display) |
| GET | `/api/plugins/<id>/assets/<file>` | Serve plugin static files |

**Playlists:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/playlists` | Playlist management page |
| GET | `/api/playlists` | List all playlists |
| POST | `/api/playlists` | Create playlist |
| PUT | `/api/playlists/<id>` | Update playlist |
| DELETE | `/api/playlists/<id>` | Delete playlist |

**Plugin Instances:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/playlists/<id>/instances` | Add plugin to playlist |
| PUT | `/api/instances/<id>` | Update instance settings |
| DELETE | `/api/instances/<id>` | Remove from playlist |
| POST | `/api/instances/<id>/display` | Display this instance now |
| PUT | `/api/instances/<id>/reorder` | Change sort order |

**History:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/history` | Refresh history page |
| GET | `/api/history` | Paginated refresh logs |

**API Keys:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/api-keys` | API keys management page |
| POST | `/api/credentials` | Add API credential |
| PUT | `/api/credentials/<id>` | Update credential |
| DELETE | `/api/credentials/<id>` | Delete credential |

---

## 9. Image Processing Pipeline

### 9.1 Generation Methods

**Method 1: Programmatic (PIL/Pillow)**
- Plugin creates images directly using PIL drawing operations
- Used by: clock, task_calendar, image_upload, apod, newspaper, ai_image
- Full control over pixel-level rendering
- Best for: geometric layouts, charts, calendars

**Method 2: HTML/CSS Rendering (Chromium)**
- Plugin provides Jinja2 HTML template + CSS
- BasePlugin renders via headless Chromium, captures screenshot as PIL Image
- Used by: weather, ai_text, screenshot
- Best for: text-heavy layouts, responsive designs, complex typography

**Method 3: Remote Image Fetch**
- Plugin fetches image from external URL
- Returns PIL Image from HTTP response
- Used by: apod, newspaper, ai_image
- Subject to network availability

### 9.2 Post-Processing Pipeline

After a plugin returns a PIL Image, the pipeline applies:

1. **Orientation** — Rotate based on device orientation + invert setting
2. **Resize** — Aspect-ratio-preserving crop and resize to target resolution
   - Default: center crop to fill
   - Optional: `keep-width` mode (no center crop, stretches width)
3. **Enhancement** — Apply device-level image adjustments:
   - Brightness (0.0 - 2.0, default 1.0)
   - Contrast (0.0 - 2.0, default 1.0)
   - Saturation (0.0 - 2.0, default 1.0)
   - Sharpness (0.0 - 2.0, default 1.0)
4. **Color Palette Conversion** — Map to target display's color palette
   - Floyd-Steinberg dithering for B/W
   - Nearest-color mapping for multi-color displays
5. **Hash Computation** — SHA-256 of processed image bytes
6. **Cache** — Save processed image to disk
7. **Transport** — Push to ESP32 display target(s)

### 9.3 Image Caching Strategy

- Each plugin instance has a `cached_image_path`
- Cached images stored in: `media/plugin_cache/<plugin_id>/<instance_id>/`
- Cache is invalidated when:
  - Instance settings change
  - Manual refresh is triggered
  - Refresh interval/schedule triggers regeneration
- Cache is used when:
  - Playlist cycles to an instance that doesn't need refresh yet
  - Avoids redundant API calls (important for paid APIs like OpenAI)

---

## 10. Authentication & Credentials

### 10.1 API Key Management

- Store API keys encrypted in the `api_credentials` table
- Encrypt at rest using Django's signing framework or Fernet symmetric encryption
- Keys accessible to plugins via `device.get_api_key("service_name")`
- Web UI for CRUD operations on keys
- Environment variables as fallback (for backward compatibility)

### 10.2 Google Calendar OAuth2

**Current Flow (preserve):**
1. User runs CLI script to initiate OAuth2 flow
2. Browser opens Google consent screen
3. Local callback server receives authorization code
4. Exchange code for access + refresh tokens
5. Store tokens in database (`api_credentials` table, `metadata` field)

**Improvements:**
- Move token storage from filesystem to database
- Add web UI flow: "Connect Google Calendar" button that initiates OAuth
- OAuth callback handled by Django view instead of standalone script
- Automatic token refresh in Celery task (before expiry)
- Graceful degradation if credentials invalid

### 10.3 TickTick Authentication

- Similar OAuth2 flow as Google Calendar
- Store tokens in `api_credentials` table
- Web UI integration for connection setup

---

## 11. Docker Environment

### 11.1 Docker Compose (`docker-compose.yml`)

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - media_data:/app/media
    depends_on:
      - db
      - redis
    env_file: .env
    command: python manage.py runserver 0.0.0.0:8000

  worker:
    build: .
    command: celery -A inkypi worker -l info -c 2
    volumes:
      - .:/app
      - media_data:/app/media
    depends_on:
      - db
      - redis
    env_file: .env

  beat:
    build: .
    command: celery -A inkypi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file: .env

  db:
    image: postgres:16-alpine
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: inkypi
      POSTGRES_USER: inkypi
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
  media_data:
```

### 11.2 Dockerfile

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000

CMD ["gunicorn", "inkypi.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

### 11.3 Environment Variables (`.env`)

```bash
# Django
DJANGO_SECRET_KEY=<generated>
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=*

# Database
DB_PASSWORD=<generated>
DATABASE_URL=postgres://inkypi:${DB_PASSWORD}@db:5432/inkypi

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# API Keys (optional, can also be set via web UI)
OPEN_WEATHER_MAP_SECRET=
OPEN_AI_SECRET=
NASA_SECRET=
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=

# Display
DEFAULT_TIMEZONE=America/New_York
```

### 11.4 Development Workflow

```bash
# Start all services
docker compose up -d

# Run migrations
docker compose exec app python manage.py migrate

# Create superuser
docker compose exec app python manage.py createsuperuser

# View logs
docker compose logs -f app worker

# Run plugin tests
docker compose exec app python manage.py test plugins

# Shell access
docker compose exec app python manage.py shell

# Stop all services
docker compose down
```

---

## 12. Django Project Structure

```
inkypi/
├── docker-compose.yml
├── Dockerfile
├── .env
├── requirements.txt
├── manage.py
├── inkypi/                          # Django project
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py                    # Celery app config
├── core/                            # Core app
│   ├── models.py                    # Device, ImageSettings, DisplayTarget
│   ├── views.py                     # Home, settings pages
│   ├── admin.py
│   ├── tasks.py                     # Celery tasks (refresh check, cleanup)
│   ├── services/
│   │   ├── display_service.py       # Image transport to ESP32
│   │   ├── image_service.py         # Image processing pipeline
│   │   └── refresh_service.py       # Refresh logic (playlist resolution)
│   ├── utils/
│   │   ├── image_utils.py           # PIL helpers, resize, enhance, dither
│   │   ├── time_utils.py            # Time/interval calculations
│   │   └── crypto_utils.py          # API key encryption
│   └── templates/
│       ├── base.html
│       ├── home.html
│       └── settings.html
├── plugins/                         # Plugins app
│   ├── models.py                    # Plugin, PluginInstance
│   ├── views.py                     # Plugin config pages, manual refresh
│   ├── admin.py
│   ├── registry.py                  # Plugin discovery and loading
│   ├── base_plugin.py               # BasePlugin abstract class
│   ├── templates/
│   │   └── plugin_config.html
│   └── installed/                   # Individual plugins
│       ├── clock/
│       ├── weather/
│       ├── ai_image/
│       ├── ai_text/
│       ├── apod/
│       ├── newspaper/
│       ├── image_upload/
│       ├── screenshot/
│       └── task_calendar/
├── playlists/                       # Playlists app
│   ├── models.py                    # Playlist, PlaylistPlugin
│   ├── views.py                     # Playlist CRUD pages
│   ├── admin.py
│   └── templates/
│       └── playlist.html
├── history/                         # History app
│   ├── models.py                    # RefreshLog
│   ├── views.py
│   └── templates/
│       └── history.html
├── credentials/                     # Credentials app
│   ├── models.py                    # ApiCredential
│   ├── views.py
│   └── templates/
│       └── api_keys.html
├── static/
│   ├── css/
│   ├── js/
│   ├── fonts/
│   ├── icons/
│   └── images/
├── media/                           # User uploads + cached images
│   ├── uploads/
│   └── plugin_cache/
└── scripts/
    └── test_plugin.py               # Plugin testing utility
```

---

## 13. Migration Path

### 13.1 Data Migration

Since v1 uses `device.json` and v2 uses PostgreSQL, provide a management command:

```bash
docker compose exec app python manage.py migrate_from_v1 /path/to/device.json
```

This command should:
1. Read `device.json`
2. Create `Device` and `DeviceImageSettings` records
3. Create `Playlist` records from `playlist_config`
4. Create `PluginInstance` records with settings
5. Migrate refresh history

### 13.2 Plugin Compatibility

- Keep the `generate_image(settings, device_config)` interface identical
- Plugin code should require minimal changes (mostly import paths)
- HTML/CSS templates and render pipeline remain the same
- Add adapter layer if `device_config` API changes

---

## 14. Testing Strategy

### 14.1 Unit Tests
- Plugin image generation (mock external APIs)
- Image processing pipeline (resize, rotate, enhance, dither)
- Playlist scheduling logic (time-based activation, cycling)
- Refresh decision logic (interval, scheduled)

### 14.2 Integration Tests
- Full refresh flow: plugin generates image -> process -> cache -> transport mock
- Playlist CRUD via API endpoints
- Plugin instance lifecycle
- OAuth2 token refresh flow

### 14.3 Plugin Testing Utility

Port the existing `scripts/test_plugin.py`:
- Test any plugin across all display sizes and orientations
- Generate sample images without hardware
- Validate plugin metadata and settings schema

```bash
docker compose exec app python manage.py test_plugin --plugin=weather --size=800x480
```

---

## 15. Non-Functional Requirements

### 15.1 Performance
- Image generation should complete within 30 seconds (60s timeout for external APIs)
- Web UI pages should load within 2 seconds
- Celery worker should handle concurrent image generation for multiple displays
- Database queries should use appropriate indexes

### 15.2 Reliability
- Celery worker auto-restarts on crash (Docker restart policy)
- Failed image generation logged with error details, doesn't crash the scheduler
- ESP32 transport failures retry 3 times with exponential backoff
- Graceful degradation: if ESP32 unreachable, cache image and retry on next cycle

### 15.3 Storage
- Image cache cleanup: remove images older than 7 days with no active reference
- Refresh log retention: keep 30 days of history, prune weekly
- Uploaded files: no auto-cleanup (user-managed)
- Database backups: daily pg_dump to volume (optional cron in Docker)

### 15.4 Security
- API keys encrypted at rest
- CSRF protection on all forms (Django default)
- No public internet exposure required (local network only)
- Django admin behind authentication
- Input validation on all API endpoints
- File upload validation (type, size limits)

---

## 16. Future Considerations (Out of Scope for v2)

These are not part of the initial rebuild but should be kept in mind:

- **Multi-display support** — Different content on different ESP32 displays
- **Mobile app** — React Native companion app for quick controls
- **Plugin marketplace** — Community plugin discovery and installation
- **Cloud sync** — Optional cloud backup of settings and playlists
- **Display groups** — Multiple ESP32s showing coordinated content (e.g., triptych)
- **WebSocket live preview** — Real-time image preview in web UI during generation
- **User accounts** — Multi-user support with permissions
