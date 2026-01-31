# InkyPi v2 - Development Phases

Phased approach to rebuilding InkyPi from scratch with Django, Docker, and ESP32 display transport.

---

## Phase 0: Project Foundation
**Goal:** Working Django app in Docker with database and task queue

### 0.1 Docker Environment Setup
- [ ] Create `Dockerfile` with Python 3.12, Pillow deps, Chromium
- [ ] Create `docker-compose.yml` with services: app, db, redis, worker, beat
- [ ] Create `.env.example` with all environment variables
- [ ] Test `docker compose up` boots all services
- [ ] Document local development workflow

### 0.2 Django Project Scaffold
- [ ] Initialize Django project: `django-admin startproject inkypi`
- [ ] Create apps: `core`, `plugins`, `playlists`, `history`, `credentials`
- [ ] Configure settings: database, redis, static files, media
- [ ] Install dependencies: `celery`, `django-celery-beat`, `pillow`, `psycopg2`, `redis`
- [ ] Create `requirements.txt`

### 0.3 Database Models (Core)
- [ ] `Device` model (name, orientation, timezone, resolution, intervals)
- [ ] `DeviceImageSettings` model (brightness, contrast, saturation, sharpness)
- [ ] `DisplayTarget` model (ESP32 endpoints, transport type, color mode)
- [ ] Create and run initial migrations
- [ ] Set up Django admin for all models

### 0.4 Celery Setup
- [ ] Configure Celery app in `inkypi/celery.py`
- [ ] Create placeholder periodic task (heartbeat)
- [ ] Verify worker and beat containers run correctly
- [ ] Test task dispatch and execution

**Deliverable:** `docker compose up` starts Django + Postgres + Redis + Celery, admin accessible at `/admin/`

---

## Phase 1: Core Web UI (No Plugins Yet)
**Goal:** Basic web interface for device settings and display management

### 1.1 Base Templates & Static Files
- [ ] Create `base.html` template with header, nav, content blocks
- [ ] Set up static file structure: `css/`, `js/`, `fonts/`, `icons/`
- [ ] Create main stylesheet (port from v1 or start fresh)
- [ ] Add response modal component (success/error feedback)

### 1.2 Home Page
- [ ] Route: `GET /`
- [ ] Display device name and status
- [ ] Show current image preview (placeholder for now)
- [ ] Show last refresh time
- [ ] Empty plugin grid (will populate in Phase 2)

### 1.3 Settings Page
- [ ] Route: `GET /settings`
- [ ] Route: `POST /api/settings` (update device settings)
- [ ] Form fields:
  - Device name (text)
  - Orientation (select: horizontal/vertical)
  - Invert image (checkbox)
  - Timezone (autocomplete with all IANA zones)
  - Plugin cycle interval (number + unit selector)
- [ ] Image settings sliders:
  - Brightness (0.0 - 2.0)
  - Contrast (0.0 - 2.0)
  - Saturation (0.0 - 2.0)
  - Sharpness (0.0 - 2.0)
- [ ] System controls: Reboot, Shutdown buttons

### 1.4 Display Targets Page (New in v2)
- [ ] Route: `GET /displays`
- [ ] Route: `GET /api/displays` (list targets)
- [ ] Route: `POST /api/displays` (add target)
- [ ] Route: `PUT /api/displays/<id>` (update target)
- [ ] Route: `DELETE /api/displays/<id>` (remove target)
- [ ] List view showing all ESP32 displays
- [ ] Add/edit modal with fields:
  - Name
  - Transport type (HTTP/MQTT)
  - Endpoint URL or MQTT topic
  - Resolution (width × height)
  - Color mode (B/W, B/W/R, 7-color)
- [ ] Status indicator (online/offline based on last_seen)
- [ ] Test button (sends test pattern)

**Deliverable:** Working settings UI, can configure device and manage display targets

---

## Phase 2: Plugin System Foundation
**Goal:** Plugin infrastructure without individual plugins

### 2.1 Plugin Models
- [ ] `Plugin` model (plugin_id, display_name, class_name, icon_path, is_enabled)
- [ ] `PluginInstance` model (plugin, playlist, settings JSON, refresh config)
- [ ] Migrations

### 2.2 Plugin Base Class
- [ ] Create `plugins/base_plugin.py` with `BasePlugin` abstract class
- [ ] Methods:
  - `generate_image(settings, device) -> PIL.Image` (abstract)
  - `generate_settings_context() -> dict`
  - `render_html(dimensions, template, css, context) -> PIL.Image`
  - `get_plugin_dir(subpath) -> str`
  - `get_asset_url(filename) -> str`
- [ ] HTML rendering via Chromium headless

### 2.3 Plugin Registry
- [ ] Create `plugins/registry.py`
- [ ] Scan `plugins/installed/` directory on startup
- [ ] Read `plugin_meta.json` from each plugin folder
- [ ] Sync discovered plugins to database
- [ ] Load plugin classes dynamically

### 2.4 Plugin Configuration UI
- [ ] Route: `GET /plugin/<plugin_id>`
- [ ] Load plugin's `settings_form.html` template partial
- [ ] Inject plugin-specific context from `generate_settings_context()`
- [ ] "Update Now" button (manual refresh)
- [ ] "Add to Playlist" button (opens scheduling modal)

### 2.5 Image Processing Service
- [ ] Create `core/services/image_service.py`
- [ ] Functions:
  - `resize_image(image, dimensions, keep_width=False)`
  - `rotate_image(image, orientation, inverted)`
  - `apply_enhancements(image, settings)`
  - `compute_hash(image) -> str`
  - `convert_palette(image, color_mode)` (dithering for e-ink)
- [ ] Port image utilities from v1

### 2.6 Manual Refresh Flow
- [ ] Route: `POST /api/plugins/refresh`
- [ ] Accept: plugin_id, settings (JSON)
- [ ] Celery task: `generate_and_display`
  1. Load plugin class
  2. Call `generate_image()`
  3. Process image (resize, enhance, palette)
  4. Save to disk
  5. Push to display target (placeholder for Phase 5)
- [ ] Return success/error to UI

**Deliverable:** Plugin system works end-to-end, can manually refresh (image saved but not sent to ESP32 yet)

---

## Phase 3: Port Existing Plugins
**Goal:** All 9 plugins working

### 3.1 Clock Plugin
- [ ] Port `clock.py` to new structure
- [ ] Create `plugin_meta.json`
- [ ] Create `settings_form.html` (clock face selector, color pickers)
- [ ] Test all 4 clock faces:
  - Gradient clock
  - Digital clock
  - Divided clock
  - Word clock
- [ ] Verify timezone handling

### 3.2 Image Upload Plugin
- [ ] Port `image_upload.py`
- [ ] Create `plugin_meta.json`
- [ ] Create `settings_form.html` (multi-file upload)
- [ ] Handle file uploads to `media/uploads/`
- [ ] EXIF orientation correction
- [ ] Image carousel cycling
- [ ] Create `UploadedFile` and `PluginInstanceFile` models

### 3.3 Weather Plugin
- [ ] Port `weather.py`
- [ ] Create `plugin_meta.json` (requires: OPEN_WEATHER_MAP_SECRET)
- [ ] Create `settings_form.html`:
  - Location picker (Leaflet.js map)
  - Units selector
  - Toggles for each metric
  - Forecast days selector
- [ ] Port `render/weather.html` and `weather.css`
- [ ] Port weather icons to `assets/`
- [ ] Test all features: current, hourly, daily, moon phase

### 3.4 AI Image Plugin (DALL-E)
- [ ] Port `ai_image.py`
- [ ] Create `plugin_meta.json` (requires: OPEN_AI_SECRET)
- [ ] Create `settings_form.html`:
  - Text prompt input
  - Model selector (DALL-E 2/3)
  - Quality selector (HD/standard)
  - Auto-enhance toggle
- [ ] Test image generation and display

### 3.5 AI Text Plugin (GPT)
- [ ] Port `ai_text.py`
- [ ] Create `plugin_meta.json` (requires: OPEN_AI_SECRET)
- [ ] Create `settings_form.html`:
  - Title input
  - Prompt textarea
  - Model selector
- [ ] Port `render/ai_text.html`
- [ ] Test text generation

### 3.6 APOD Plugin (NASA)
- [ ] Port `apod.py`
- [ ] Create `plugin_meta.json` (requires: NASA_SECRET)
- [ ] Create `settings_form.html`:
  - Custom date picker
  - Random mode toggle
- [ ] Test today, custom date, random modes

### 3.7 Newspaper Plugin
- [ ] Port `newspaper.py`
- [ ] Port `constants.py` (1000+ newspapers list)
- [ ] Create `plugin_meta.json`
- [ ] Create `settings_form.html`:
  - Newspaper search/select
  - Location filter
- [ ] Test image fetching with date fallback

### 3.8 Screenshot Plugin
- [ ] Port `screenshot.py`
- [ ] Create `plugin_meta.json`
- [ ] Create `settings_form.html`:
  - URL input
- [ ] Test Chromium screenshot capture

### 3.9 Task Calendar Plugin
- [ ] Port full plugin structure:
  - `task_calendar.py`
  - `auth/google_auth.py`
  - `services/google_calendar.py`
  - `services/ticktick.py`
  - `ui/layout.py`, `renderer.py`, `styles.py`
- [ ] Create `plugin_meta.json`
- [ ] Create `settings_form.html` (minimal - uses OAuth)
- [ ] Implement OAuth flow in web UI (see Phase 6)
- [ ] Test calendar rendering

**Deliverable:** All 9 plugins generate images correctly via manual refresh

---

## Phase 4: Playlists & Scheduling
**Goal:** Automated refresh with playlists

### 4.1 Playlist Models & Admin
- [ ] `Playlist` model (name, start_time, end_time, device, sort_order)
- [ ] Update `PluginInstance` with playlist FK, refresh settings
- [ ] Migrations
- [ ] Django admin for playlists

### 4.2 Playlist Management UI
- [ ] Route: `GET /playlists`
- [ ] Route: `GET /api/playlists` (list)
- [ ] Route: `POST /api/playlists` (create)
- [ ] Route: `PUT /api/playlists/<id>` (update)
- [ ] Route: `DELETE /api/playlists/<id>` (delete)
- [ ] List view with time ranges
- [ ] Create/edit modal (name, start time, end time)
- [ ] Per-playlist: list of plugin instances

### 4.3 Plugin Instance Management
- [ ] Route: `POST /api/playlists/<id>/instances` (add plugin to playlist)
- [ ] Route: `PUT /api/instances/<id>` (update instance)
- [ ] Route: `DELETE /api/instances/<id>` (remove)
- [ ] Route: `POST /api/instances/<id>/display` (show now)
- [ ] "Add to Playlist" modal from plugin config page:
  - Playlist selector
  - Instance name
  - Refresh type (interval / scheduled)
  - Interval: number + unit (minute/hour/day)
  - Scheduled: time picker (HH:MM)
- [ ] Edit instance settings from playlist page
- [ ] Reorder instances (drag-and-drop or arrows)

### 4.4 Refresh Scheduler
- [ ] Create `core/services/refresh_service.py`
- [ ] Logic:
  - Determine active playlist (current time vs time ranges)
  - Conflict resolution (shortest range wins)
  - Get next plugin instance in rotation
  - Check if refresh needed (interval or scheduled)
- [ ] Celery Beat task: `check_playlist_refresh` (every 60 seconds)
- [ ] Dispatch `generate_and_display` task when refresh needed
- [ ] Update `current_plugin_index` after display
- [ ] Update `latest_refresh_at` on instance

### 4.5 Skip Unchanged Images
- [ ] Store `last_image_hash` on device or instance
- [ ] Compare new image hash before display
- [ ] Skip display push if unchanged
- [ ] Log skip in refresh history

**Deliverable:** Playlists cycle automatically, instances refresh on schedule

---

## Phase 5: ESP32 Display Transport
**Goal:** Send images to ESP32 over WiFi

### 5.1 Display Service
- [ ] Create `core/services/display_service.py`
- [ ] HTTP transport:
  - POST image data to ESP32 endpoint
  - Configurable timeout and retries
  - Handle connection errors gracefully
- [ ] MQTT transport (optional):
  - Publish to topic
  - Chunked transfer for large images
  - Add Mosquitto to docker-compose if needed

### 5.2 Image Format for ESP32
- [ ] Convert PIL image to raw bitmap format
- [ ] Pack pixels for e-ink color modes:
  - B/W: 1-bit packed
  - B/W/R: 2-bit packed
  - 7-color: 4-bit packed (or display-specific format)
- [ ] Optional gzip compression
- [ ] Include metadata header (width, height, color mode)

### 5.3 Display Target Health Monitoring
- [ ] Periodic ping task (every 5 minutes)
- [ ] Update `last_seen_at` on successful contact
- [ ] Mark offline after N failed pings
- [ ] Show status in UI (green/red indicator)

### 5.4 Test Image Feature
- [ ] Generate test pattern (color bars, resolution text)
- [ ] "Test" button on display targets page
- [ ] Verify end-to-end: server → WiFi → ESP32 → e-ink

### 5.5 Error Handling & Retry
- [ ] Retry failed sends 3 times with exponential backoff
- [ ] Log failures with error details
- [ ] Cache image for retry on next cycle
- [ ] Alert in UI if display unreachable

**Deliverable:** Images display on ESP32 e-ink screen

---

## Phase 6: New v2 Features
**Goal:** Features that didn't exist in v1

### 6.1 Refresh History
- [ ] `RefreshLog` model (timestamp, plugin, playlist, type, hash, duration, error)
- [ ] Migrations
- [ ] Route: `GET /history`
- [ ] Route: `GET /api/history` (paginated)
- [ ] Table view: timestamp, plugin, type, duration, status
- [ ] Image thumbnail per entry
- [ ] Click to view full image
- [ ] Filter by plugin, playlist, date range
- [ ] Cleanup task: prune logs older than 30 days

### 6.2 API Key Management UI
- [ ] `ApiCredential` model (service_name, key_name, encrypted_value, metadata)
- [ ] Encryption/decryption utilities (Fernet)
- [ ] Migrations
- [ ] Route: `GET /settings/api-keys`
- [ ] Route: `POST /api/credentials`
- [ ] Route: `PUT /api/credentials/<id>`
- [ ] Route: `DELETE /api/credentials/<id>`
- [ ] List view with masked values
- [ ] Add/edit modal
- [ ] Delete confirmation
- [ ] Status indicator (last used, valid/invalid)

### 6.3 Google Calendar OAuth in Web UI
- [ ] Route: `GET /auth/google/start` (initiate OAuth)
- [ ] Route: `GET /auth/google/callback` (handle redirect)
- [ ] Generate authorization URL
- [ ] Exchange code for tokens
- [ ] Store tokens in `ApiCredential` (metadata field)
- [ ] "Connect Google Calendar" button in Task Calendar settings
- [ ] Show connection status
- [ ] "Disconnect" to revoke and delete tokens

### 6.4 Plugin Enable/Disable
- [ ] Add `is_enabled` field to Plugin model (already exists)
- [ ] Toggle in admin and optionally in UI
- [ ] Disabled plugins don't appear in plugin grid
- [ ] Existing instances of disabled plugins are skipped

### 6.5 Mobile-Friendly UI
- [ ] Responsive CSS (media queries)
- [ ] Touch-friendly buttons and controls
- [ ] Collapsible navigation on small screens
- [ ] Test on phone/tablet viewports

### 6.6 Backup/Restore
- [ ] Route: `GET /api/backup` (download JSON)
- [ ] Route: `POST /api/restore` (upload JSON)
- [ ] Export: device settings, playlists, plugin instances, credentials (encrypted)
- [ ] Import: validate and restore all data
- [ ] Warning before overwrite

**Deliverable:** All new v2 features complete

---

## Phase 7: Polish & Production Ready
**Goal:** Stable, deployable application

### 7.1 Error Handling & Logging
- [ ] Consistent error responses across all API endpoints
- [ ] Sentry integration for error tracking
- [ ] Structured logging with log levels
- [ ] Request/response logging for debugging

### 7.2 Performance Optimization
- [ ] Database query optimization (select_related, indexes)
- [ ] Image caching strategy (avoid regenerating unchanged)
- [ ] Static file caching headers
- [ ] Celery task priorities (manual refresh = high)

### 7.3 Security Hardening
- [ ] CSRF protection on all forms
- [ ] Input validation on all endpoints
- [ ] File upload validation (type, size)
- [ ] Rate limiting on API endpoints
- [ ] Secure headers (X-Frame-Options, etc.)

### 7.4 Testing
- [ ] Unit tests for image processing
- [ ] Unit tests for scheduling logic
- [ ] Integration tests for refresh flow
- [ ] Plugin test utility (`manage.py test_plugin`)
- [ ] CI pipeline (GitHub Actions)

### 7.5 Documentation
- [ ] README with setup instructions
- [ ] Plugin development guide
- [ ] API documentation
- [ ] Troubleshooting guide
- [ ] Update CLAUDE.md for new structure

### 7.6 Deployment
- [ ] Production docker-compose (no dev volumes)
- [ ] Gunicorn instead of runserver
- [ ] Nginx reverse proxy (optional)
- [ ] Auto-restart policies
- [ ] Health check endpoints
- [ ] First-run setup wizard (optional)

**Deliverable:** Production-ready application

---

## Timeline Estimate

| Phase | Description | Complexity |
|-------|-------------|------------|
| 0 | Project Foundation | Medium |
| 1 | Core Web UI | Medium |
| 2 | Plugin System | High |
| 3 | Port Plugins | High (9 plugins) |
| 4 | Playlists & Scheduling | Medium |
| 5 | ESP32 Transport | Medium |
| 6 | New v2 Features | Medium |
| 7 | Polish & Production | Medium |

**MVP (Phases 0-2):** Basic working system with plugin infrastructure
**Alpha (Phases 0-4):** All plugins, scheduling works
**Beta (Phases 0-5):** ESP32 integration complete
**Release (Phases 0-7):** Production ready

---

## Dependencies Between Phases

```
Phase 0 (Foundation)
    ↓
Phase 1 (Core UI)
    ↓
Phase 2 (Plugin System) ──→ Phase 3 (Port Plugins)
    ↓                              ↓
Phase 4 (Scheduling) ←─────────────┘
    ↓
Phase 5 (ESP32 Transport)
    ↓
Phase 6 (New Features) ← can start partially during Phase 4/5
    ↓
Phase 7 (Polish)
```

**Parallel work possible:**
- Phase 3 (plugins) can be done incrementally alongside Phase 4
- Phase 6.1-6.2 (history, API keys) can start during Phase 4
- Phase 6.5 (mobile UI) can be done anytime after Phase 1
- Phase 7 (testing, docs) should be ongoing throughout

---

## Getting Started Checklist

1. [ ] Set up development environment (Docker, IDE)
2. [ ] Initialize git repository for v2
3. [ ] Create Docker environment (Phase 0.1)
4. [ ] Scaffold Django project (Phase 0.2)
5. [ ] Create first model and migration (Phase 0.3)
6. [ ] Verify Celery works (Phase 0.4)
7. [ ] Begin Phase 1...
