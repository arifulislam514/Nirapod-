# Child Safety Alert System — Full Codebase & API Explanation

---

## Table of Contents

1. [How the whole system works](#1-how-the-whole-system-works)
2. [Project structure](#2-project-structure)
3. [Configuration files](#3-configuration-files)
4. [App 1 — accounts](#4-app-1--accounts)
5. [App 2 — devices](#5-app-2--devices)
6. [App 3 — locations](#6-app-3--locations)
7. [App 4 — alerts](#7-app-4--alerts)
8. [App 5 — geofences](#8-app-5--geofences)
9. [All APIs — complete reference](#9-all-apis--complete-reference)

---

## 1. How the whole system works

```
Parent (React Frontend)
        │
        │  JWT Token in every request header
        │  Authorization: JWT eyJhbGc...
        ▼
Django REST API (port 8000)
        │
        ├── PostgreSQL (stores all data permanently)
        ├── Redis      (message broker for Celery + WebSocket)
        ├── Celery     (sends SMS in background)
        └── WebSocket  (pushes live updates to frontend instantly)
        ▲
        │  X-Device-Token header
        │  (static 64-char hex token)
        │
ESP32 Device (hardware attached to child)
```

**Step-by-step data flow:**

1. Parent registers on the app → creates an account → logs in → gets a JWT token
2. Parent registers an ESP32 device in the app → gets a `device_token`
3. The `device_token` is uploaded to the ESP32 hardware
4. ESP32 sends GPS coordinates every few seconds → `POST /api/locations/`
5. Django saves the GPS reading → pushes it live to parent's dashboard via WebSocket
6. If child presses panic button → ESP32 sends `POST /api/alerts/`
7. Django saves the alert → Celery task sends SMS to parent's phone → WebSocket pushes alert to dashboard
8. Parent sees the alert on dashboard instantly, checks the map, calls the child, marks it resolved

---

## 2. Project Structure

```
child_safety_backend/               ← Django project root
│
├── child_safety_backend/           ← Project configuration package
│   ├── settings.py                 ← All settings (DB, Redis, JWT, etc.)
│   ├── urls.py                     ← Root URL routing
│   ├── asgi.py                     ← ASGI entry point (HTTP + WebSocket)
│   ├── celery.py                   ← Celery app setup
│   ├── wsgi.py                     ← WSGI entry point (not used — we use ASGI)
│   └── schema_filters.py           ← Swagger tag renaming hook
│
├── accounts/                       ← User authentication app
│   ├── models.py                   ← CustomUser model
│   ├── serializers.py              ← Register + Profile serializers
│   ├── views.py                    ← MeView (GET profile)
│   └── urls.py                     ← /api/auth/users/me/
│
├── devices/                        ← ESP32 device registry app
│   ├── models.py                   ← Device model
│   ├── authentication.py           ← DeviceTokenAuthentication class
│   ├── serializers.py              ← DeviceSerializer
│   ├── views.py                    ← DeviceViewSet
│   └── urls.py                     ← /api/devices/
│
├── locations/                      ← GPS tracking app
│   ├── models.py                   ← LocationReading model
│   ├── serializers.py              ← LocationReadingSerializer
│   ├── services.py                 ← record_location() function
│   ├── views.py                    ← LocationViewSet
│   └── urls.py                     ← /api/locations/
│
├── alerts/                         ← Alert system app
│   ├── models.py                   ← AlertEvent model
│   ├── serializers.py              ← AlertEventSerializer
│   ├── views.py                    ← AlertEventViewSet
│   ├── tasks.py                    ← send_sms_alert() Celery task
│   ├── consumers.py                ← DeviceConsumer WebSocket handler
│   ├── routing.py                  ← WebSocket URL routing
│   └── urls.py                     ← /api/alerts/
│
├── geofences/                      ← Safe zone management app
│   ├── models.py                   ← Geofence model (with Haversine math)
│   ├── serializers.py              ← GeofenceSerializer
│   ├── views.py                    ← GeofenceViewSet
│   └── urls.py                     ← /api/geofences/
│
├── manage.py                       ← Django management commands
├── requirements.txt                ← All Python packages
└── .env.example                    ← Environment variables template
```

---

## 3. Configuration Files

### `settings.py` — the brain of the whole project

**INSTALLED_APPS**
```python
'daphne',        # MUST be first — runs the ASGI server (HTTP + WebSocket)
'rest_framework' # Django REST Framework — powers all our APIs
'corsheaders'    # Allows React frontend (different port) to call our API
'channels'       # Django Channels — powers WebSocket real-time feature
'django_filters' # Adds ?device=uuid filtering to list endpoints
'drf_spectacular'# Auto-generates Swagger docs at /api/docs/
'djoser'         # Handles register, login, password reset (built-in)
```

**DATABASES** — connects to PostgreSQL using values from `.env` file:
```python
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
```

**CHANNEL_LAYERS** — connects to Redis for WebSocket messages:
```python
REDIS_URL=redis://localhost:6379/0
```

**CELERY** — also uses Redis as the task queue broker:
```python
CELERY_BROKER_URL = REDIS_URL  # tasks go into Redis queue
CELERY_RESULT_BACKEND = REDIS_URL  # results stored in Redis
```

**REST_FRAMEWORK** — two authenticators registered globally:
```python
'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    # ↑ Checks Authorization: JWT <token> header
    'devices.authentication.DeviceTokenAuthentication',
    # ↑ Checks X-Device-Token header
]
```
Django tries JWT first. If no JWT header, it tries Device Token. If neither, the request is anonymous (and will fail on protected endpoints).

**SIMPLE_JWT** — token lifetimes:
```python
ACCESS_TOKEN_LIFETIME  = 12 hours   # frontend uses this for API calls
REFRESH_TOKEN_LIFETIME = 30 days    # used to get new access tokens
AUTH_HEADER_TYPES      = ('JWT',)   # prefix is JWT not Bearer
```

**DJOSER** — tells Djoser to use our custom serializers:
```python
'LOGIN_FIELD': 'email'              # login with email, not username
'USER_CREATE_PASSWORD_RETYPE': True # require re_password on register
'SERIALIZERS': {
    'user_create': 'accounts.serializers.RegisterSerializer',
    'current_user': 'accounts.serializers.UserProfileSerializer',
}
```

---

### `urls.py` — the traffic controller

Every HTTP request comes here first. Django reads the URL and sends the request to the right view.

```python
/admin/                 → Django admin panel
/api/schema/            → Raw OpenAPI JSON schema
/api/docs/              → Swagger UI (human-readable)
/api/redoc/             → ReDoc UI (alternative docs)
/api/auth/users/me/     → MeView (our custom profile endpoint)
/api/auth/              → All Djoser routes (register, login, password reset, etc.)
/api/devices/           → DeviceViewSet
/api/locations/         → LocationViewSet
/api/alerts/            → AlertEventViewSet
/api/geofences/         → GeofenceViewSet
```

---

### `asgi.py` — HTTP + WebSocket in one server

```python
application = ProtocolTypeRouter({
    'http':      django_asgi_app,        # normal HTTP → goes to Django views
    'websocket': URLRouter(websocket_urlpatterns),  # ws:// → goes to consumers.py
})
```

ASGI (Async Server Gateway Interface) is what allows Django to handle both regular HTTP requests AND persistent WebSocket connections at the same time. Daphne is the server that runs ASGI.

---

### `celery.py` — background task runner

```python
app = Celery('child_safety_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
# ↑ Automatically finds tasks.py in every app
```

Celery runs as a separate process (Window 2 in your setup). When an alert is triggered, the view calls `send_sms_alert.delay(alert_id)`. The `.delay()` puts the task into the Redis queue and returns immediately — the view doesn't wait. Celery picks up the task from Redis and runs it in the background.

---

## 4. App 1 — accounts

### `models.py` — CustomUser

```python
class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, phone, password, ...):
        # Creates a regular user — called during registration
    def create_superuser(self, email, name, phone, password, ...):
        # Creates admin — called by `python manage.py createsuperuser`
```

Why a custom manager? Because we removed `username` from the model. Django's default manager always tries to set `username`. Our manager only sets `email`, `name`, `phone`.

```python
class CustomUser(AbstractUser):
    username = None           # Removed — we don't use it
    id       = UUIDField      # UUID instead of auto-increment integer
    email    = EmailField     # Used to log in (USERNAME_FIELD = 'email')
    name     = CharField      # Full name
    phone    = CharField      # SMS alert recipient phone number
    role     = CharField      # 'parent' or 'admin'
    created_at = DateTimeField

    USERNAME_FIELD  = 'email'          # login with email
    REQUIRED_FIELDS = ['name', 'phone']# required for createsuperuser
```

**Why UUID instead of integer ID?**
UUIDs like `a1b2c3d4-e5f6-7890-abcd-ef1234567890` are impossible to guess. If you use integer IDs (1, 2, 3...), anyone can guess `GET /api/users/2/` and try to access someone else's account.

---

### `serializers.py`

**RegisterSerializer** — used when someone calls `POST /api/auth/users/` to create an account:
```python
fields = ('id', 'email', 'name', 'phone', 'password', 're_password')
# re_password is declared explicitly as CharField because it's NOT a model field
# Djoser uses it for password confirmation validation, then discards it
```

**UserProfileSerializer** — used for the profile endpoint `GET /api/auth/users/me/`:
```python
fields = ('id', 'email', 'name', 'phone', 'role', 'created_at')
read_only_fields = fields  # all read-only, this is just for display
```

---

### `views.py` — MeView

```python
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    # ↑ Only logged-in users can access this

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)
        # request.user is automatically the logged-in user from the JWT token
```

This is the simplest possible view. `request.user` is populated by `JWTAuthentication` which reads the token from the `Authorization: JWT <token>` header and looks up the user in the database.

---

## 5. App 2 — devices

### `models.py` — Device

```python
class Device(models.Model):
    id           = UUIDField    # unique device ID
    owner        = ForeignKey(CustomUser)  # which parent owns this device
    name         = CharField    # e.g. "Riya School Device"
    device_token = CharField(unique=True)  # 64-char hex, sent by ESP32 in header
    is_active    = BooleanField # false = device is blocked
    last_seen    = DateTimeField# updated every time ESP32 sends GPS
    battery_pct  = IntegerField # 0–100, updated with every GPS reading
```

One parent (`CustomUser`) can have many devices. If a parent has 2 children, they register 2 devices. `on_delete=CASCADE` means if the parent account is deleted, all their devices are deleted too.

---

### `authentication.py` — DeviceTokenAuthentication

This is a custom authentication class — something Django REST Framework doesn't provide by default. We built it because ESP32 hardware cannot handle JWT (tokens expire, need refresh logic, etc.).

```python
def authenticate(self, request):
    token = request.headers.get('X-Device-Token')
    # ↑ Read the custom header

    if not token:
        return None  # No token? Fall through to JWT authentication
        # Returning None means "I can't handle this, try the next authenticator"

    device = Device.objects.get(device_token=token, is_active=True)
    # ↑ Look up which device this token belongs to
    # Raises DoesNotExist if token is wrong → AuthenticationFailed exception

    return (device.owner, device)
    # ↑ Return (user, auth) tuple
    # This sets request.user = device.owner (the parent)
    # And request.auth = device (the Device object)
    # So in views, we can do: device = request.auth
```

**Why `select_related('owner')`?** Without it, accessing `device.owner` would run a second SQL query. With it, Django fetches both device and owner in one SQL JOIN query. More efficient.

---

### `serializers.py`

**DeviceSerializer** — for listing and creating devices:
```python
device_token  → read_only  # auto-generated on create, never editable
last_seen     → read_only  # auto-updated by ESP32 posts
owner_email   → read_only  # comes from owner.email (nested field)

def create(self, validated_data):
    validated_data['device_token'] = secrets.token_hex(32)
    # ↑ Generates a cryptographically secure random 64-char hex string
    # secrets.token_hex(32) = 32 bytes = 64 hex characters
    validated_data['owner'] = self.context['request'].user
    # ↑ Auto-set the owner to the currently logged-in user
```

**DeviceUpdateSerializer** — for updating devices (PUT/PATCH). Only allows changing `name` and `is_active`. Everything else (token, owner, last_seen) cannot be changed by the user.

---

### `views.py` — DeviceViewSet

```python
class DeviceViewSet(viewsets.ModelViewSet):
    # ModelViewSet automatically provides:
    # create()         → POST /api/devices/
    # list()           → GET  /api/devices/
    # retrieve()       → GET  /api/devices/{id}/
    # update()         → PUT  /api/devices/{id}/
    # partial_update() → PATCH /api/devices/{id}/
    # destroy()        → DELETE /api/devices/{id}/

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return DeviceUpdateSerializer  # only name + is_active changeable
        return DeviceSerializer           # full data for list/create/retrieve

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Device.objects.none()
            # ↑ When Swagger generates docs, request.user is AnonymousUser
            # This guard returns empty queryset so no crash happens
        return Device.objects.filter(owner=self.request.user)
        # ↑ Parents can ONLY see their OWN devices. Never other users' devices.

    def destroy(self, request, *args, **kwargs):
        device = self.get_object()
        device.is_active = False          # Soft delete — don't actually delete
        device.save(update_fields=['is_active'])
        return Response({'detail': 'Device deactivated.'})
        # We soft-delete because deleting would also delete all location history
        # and alerts (CASCADE). We want to keep that history.
```

---

## 6. App 3 — locations

### `models.py` — LocationReading

```python
class LocationReading(models.Model):
    id        = UUIDField
    device    = ForeignKey(Device)  # which device sent this reading
    latitude  = DecimalField(max_digits=9, decimal_places=6)
    # ↑ 6 decimal places = ~0.1 metre accuracy
    # e.g. 23.726008 is accurate to about 11cm
    longitude = DecimalField(max_digits=9, decimal_places=6)
    accuracy  = FloatField(null=True)  # GPS accuracy from satellite signal
    speed     = FloatField(null=True)  # metres per second
    timestamp = DateTimeField(auto_now_add=True, db_index=True)
    # ↑ db_index=True creates a database index on this column
    # Makes queries like "get readings from last hour" much faster

    class Meta:
        indexes = [
            models.Index(fields=['device', '-timestamp'])
            # ↑ Compound index: makes "get latest reading for device X" very fast
            # The minus sign means descending order (newest first)
        ]
```

---

### `services.py` — record_location()

This is the **service layer** — business logic separated from the view. The view just handles HTTP. The service handles the actual work.

```python
def record_location(device, data) -> LocationReading:

    # STEP 1: Save to database
    reading = LocationReading.objects.create(
        device=device,
        latitude=data['latitude'],
        longitude=data['longitude'],
        accuracy=data.get('accuracy'),   # .get() returns None if key missing
        speed=data.get('speed'),
    )

    # STEP 2: Update device heartbeat
    device.last_seen = timezone.now()
    if 'battery_pct' in data:
        device.battery_pct = data['battery_pct']
    device.save(update_fields=['last_seen', 'battery_pct'])
    # update_fields is important — only saves those 2 columns, not the whole row
    # Much more efficient for frequently-updated fields

    # STEP 3: Push real-time update to parent dashboard
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{device.id}',     # ← channel group name
        {
            'type': 'location_update',  # ← which handler to call in consumers.py
            'lat': str(reading.latitude),
            'lon': str(reading.longitude),
            'timestamp': reading.timestamp.isoformat(),
        }
    )
    # async_to_sync() wraps an async function so we can call it from sync code
    # group_send() broadcasts to everyone connected to this device's channel group

    return reading
```

---

### `views.py` — LocationViewSet

The key part is the custom `create()` method:

```python
def create(self, request, *args, **kwargs):
    device = request.auth
    # ↑ request.auth is the Device object set by DeviceTokenAuthentication
    # If someone uses JWT instead of Device Token, request.auth is the token string
    # So we check isinstance(device, Device) to ensure it's really a Device

    if not isinstance(device, Device):
        raise PermissionDenied('This endpoint requires X-Device-Token header.')

    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    # ↑ Validates the JSON body. If invalid, raises 400 error automatically.

    reading = record_location(device, {
        'latitude': serializer.validated_data['latitude'],
        'longitude': serializer.validated_data['longitude'],
        'accuracy': serializer.validated_data.get('accuracy'),
        'speed': serializer.validated_data.get('speed'),
        'battery_pct': request.data.get('battery_pct'),
        # battery_pct is not in the serializer (not a model field for LocationReading)
        # so we read it directly from request.data and pass it to the service
    })

    return Response(LocationReadingSerializer(reading).data, status=201)
```

The `latest` action is a custom endpoint added with `@action`:

```python
@action(detail=False, methods=['get'], url_path='latest')
def latest(self, request):
    # detail=False  → URL is /api/locations/latest/ (not /api/locations/{id}/latest/)
    # url_path='latest' → the URL suffix after the base URL

    device_id = request.query_params.get('device')
    # request.query_params is the ?device=uuid part of the URL

    reading = LocationReading.objects
        .filter(device__id=device_id, device__owner=request.user)
        # device__owner = follow the ForeignKey to Device, then to its owner
        # This ensures a parent can only see their own device's readings
        .order_by('-timestamp')  # newest first (minus = descending)
        .first()                 # get only the first result (1 reading)
```

---

## 7. App 4 — alerts

### `models.py` — AlertEvent

```python
class AlertEvent(models.Model):
    ALERT_TYPES = [
        ('PANIC',    'Panic Button'),
        ('GEOFENCE', 'Geofence Breach'),
        ('MOTION',   'Suspicious Motion'),
    ]
    # First value = stored in DB, Second value = human-readable display

    id         = UUIDField
    device     = ForeignKey(Device)
    alert_type = CharField(choices=ALERT_TYPES)
    latitude   = DecimalField(null=True)   # where the alert happened
    longitude  = DecimalField(null=True)
    sms_sent   = BooleanField(default=False)    # did SMS go out?
    sms_sent_at = DateTimeField(null=True)      # when was it sent?
    resolved   = BooleanField(default=False)    # parent acknowledged?
    timestamp  = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['device', '-timestamp']),  # fast device queries
            models.Index(fields=['resolved']),  # fast ?resolved=false filter
        ]
```

---

### `tasks.py` — send_sms_alert (Celery task)

```python
@shared_task
def send_sms_alert(alert_id: str):
    # @shared_task → Celery picks this up and runs it in a separate worker process
    # alert_id is a string because Celery serializes arguments as JSON

    alert = AlertEvent.objects
        .select_related('device__owner')
        # ↑ One query to get: alert → device → owner
        # Without this: 3 separate queries
        .get(id=alert_id)

    # Build SMS message
    parent_phone = alert.device.owner.phone
    msg = f'SAFETY ALERT ({alert.alert_type}): Lat {alert.latitude}...'

    # DEV MODE: Print to terminal instead of real SMS
    print('📱  SIMULATED SMS')
    print(f'   To: {parent_phone}')
    print(f'   Message: {msg}')

    # Update SMS status in DB
    alert.sms_sent = True
    alert.sms_sent_at = timezone.now()
    alert.save(update_fields=['sms_sent', 'sms_sent_at'])

    # Push WebSocket notification
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{alert.device_id}',
        {
            'type': 'alert_event',      # → calls alert_event() in consumers.py
            'alert_type': alert.alert_type,
            'lat': str(alert.latitude),
            'lon': str(alert.longitude),
        }
    )
```

**How Celery works here:**

1. `AlertEventViewSet.create()` calls `send_sms_alert.delay(str(alert.id))`
2. `.delay()` puts the task into Redis queue and returns immediately (non-blocking)
3. The HTTP response is sent to ESP32 right away (fast)
4. Celery worker (running in Window 2) picks up the task from Redis
5. Celery runs `send_sms_alert()` in the background
6. SMS is sent + WebSocket push happens

Without Celery: the HTTP response would wait for SMS to send (slow, risky if SMS API is down).

---

### `consumers.py` — DeviceConsumer (WebSocket)

```python
class DeviceConsumer(AsyncWebsocketConsumer):
    # AsyncWebsocketConsumer → handles WebSocket connections asynchronously
    # Each browser tab that connects gets its own DeviceConsumer instance

    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        # ↑ Extract device_id from the WebSocket URL: ws://host/ws/device/{device_id}/

        self.group_name = f'device_{self.device_id}'
        # ↑ Each device has its own channel group
        # All browsers watching the same device join the same group

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # ↑ Add this connection to the group
        # self.channel_name is a unique ID for this specific connection

        await self.accept()
        # ↑ Confirm the WebSocket connection (must call this to proceed)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # ↑ Remove from group when browser disconnects (tab closed, network lost)

    async def location_update(self, event):
        # Called when services.py does group_send with type='location_update'
        # 'type': 'location_update' → Django Channels calls location_update() method
        await self.send(text_data=json.dumps({
            'type': 'location',
            'lat': event['lat'],
            'lon': event['lon'],
            'ts': event['timestamp'],
        }))
        # Sends JSON to the browser over WebSocket

    async def alert_event(self, event):
        # Called when tasks.py does group_send with type='alert_event'
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'alert_type': event['alert_type'],
            'lat': event.get('lat'),
            'lon': event.get('lon'),
        }))
```

**WebSocket flow summary:**
```
Browser connects to ws://localhost:8000/ws/device/abc-123/
    → DeviceConsumer.connect() runs
    → Browser joins group "device_abc-123"

ESP32 posts GPS → services.py → group_send("device_abc-123", type="location_update")
    → DeviceConsumer.location_update() runs on the server
    → Sends JSON to browser instantly
    → Browser receives: {"type": "location", "lat": "23.72", "lon": "90.40", "ts": "..."}

ESP32 triggers alert → tasks.py → group_send("device_abc-123", type="alert_event")
    → DeviceConsumer.alert_event() runs
    → Browser receives: {"type": "alert", "alert_type": "PANIC", "lat": "...", "lon": "..."}
```

---

## 8. App 5 — geofences

### `models.py` — Geofence

```python
class Geofence(models.Model):
    id       = UUIDField
    device   = ForeignKey(Device)   # each device has its own set of fences
    name     = CharField            # 'Home', 'School', etc.
    latitude = DecimalField         # centre of the safe zone
    longitude = DecimalField
    radius_m = IntegerField         # radius in metres (100 = 100m circle)
    is_active = BooleanField        # false = temporarily disabled

    def contains(self, lat: float, lon: float) -> bool:
        """
        Haversine formula — calculates real-world distance between two GPS points.
        Returns True if the given point is inside this geofence circle.
        """
        R = 6_371_000  # Earth's radius in metres (Earth is not flat)
        # The formula accounts for Earth's curvature
        # Simple Pythagoras would give wrong answers for GPS coordinates
        ...
        return distance_m <= self.radius_m
```

The `contains()` method uses the **Haversine formula** — a mathematical formula for calculating distances on a sphere (the Earth). The ESP32 can call this (or implement it in C++) to check if the child is outside a safe zone before sending a GEOFENCE alert.

---

### `serializers.py`

```python
def validate_device(self, device):
    """Custom field-level validation."""
    request = self.context['request']
    if device.owner != request.user:
        raise serializers.ValidationError('You do not own this device.')
    # ↑ Security check: parent A cannot create a geofence on parent B's device
    # This runs automatically before .save() is called
    return device
```

---

## 9. All APIs — Complete Reference

### Authentication endpoints (Djoser + SimpleJWT)

---

#### POST `/api/auth/users/` — Register

No authentication needed.

**Send:**
```json
{
    "email": "parent@example.com",
    "name": "Rahim Uddin",
    "phone": "01711111111",
    "password": "StrongPass123!",
    "re_password": "StrongPass123!"
}
```

**Success 201:**
```json
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "parent@example.com",
    "name": "Rahim Uddin",
    "phone": "01711111111"
}
```

**Error 400:**
```json
{
    "email": ["user with this email already exists."],
    "password": ["This password is too short."]
}
```

---

#### POST `/api/auth/jwt/create/` — Login

No authentication needed.

**Send:**
```json
{
    "email": "parent@example.com",
    "password": "StrongPass123!"
}
```

**Success 200:**
```json
{
    "access": "eyJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiJ9..."
}
```
Save both tokens. Use `access` in every request header. Use `refresh` to renew after 12 hours.

**Error 401:**
```json
{"detail": "No active account found with the given credentials"}
```

---

#### POST `/api/auth/jwt/refresh/` — Refresh token

No authentication needed.

**Send:**
```json
{"refresh": "eyJhbGciOiJIUzI1NiJ9..."}
```

**Success 200:**
```json
{"access": "eyJhbGciOiJIUzI1NiJ9.NEW_TOKEN..."}
```

---

#### POST `/api/auth/jwt/verify/` — Verify token

No authentication needed.

**Send:**
```json
{"token": "eyJhbGciOiJIUzI1NiJ9..."}
```

**Success 200:** `{}` (empty object)
**Error 401:** token is invalid or expired

---

#### GET `/api/auth/users/me/` — Get my profile

**Header:** `Authorization: JWT your-access-token`

**Success 200:**
```json
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "parent@example.com",
    "name": "Rahim Uddin",
    "phone": "01711111111",
    "role": "parent",
    "created_at": "2025-01-15T10:30:00Z"
}
```

---

#### POST `/api/auth/users/set_password/` — Change password

**Header:** `Authorization: JWT your-access-token`

**Send:**
```json
{
    "current_password": "OldPass123!",
    "new_password": "NewPass456!",
    "re_new_password": "NewPass456!"
}
```

**Success:** `204 No Content`

---

#### POST `/api/auth/users/reset_password/` — Forgot password

No authentication needed.

**Send:**
```json
{"email": "parent@example.com"}
```

**Success:** `204 No Content` — Django prints the reset email in the terminal (dev mode)

---

#### POST `/api/auth/users/reset_password_confirm/` — Confirm reset

**Send:**
```json
{
    "uid": "MQ",
    "token": "abc123-def456",
    "new_password": "BrandNew789!",
    "re_new_password": "BrandNew789!"
}
```

**Success:** `204 No Content`

---

### Devices endpoints

All require: `Authorization: JWT your-access-token`

---

#### POST `/api/devices/` — Register a device

**Send:**
```json
{"name": "Riya School Device"}
```

**Success 201:**
```json
{
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "owner_email": "parent@example.com",
    "name": "Riya School Device",
    "device_token": "a3f9c2e1b4d87f2e9c1a0b3d5e8f2a4c6e9b1d3f5a7c9e1b3d5f7a9c1e3b5d7",
    "is_active": true,
    "last_seen": null,
    "battery_pct": 100
}
```
⚠️ Save `device_token` now — flash it to the ESP32 hardware.

---

#### GET `/api/devices/` — List my devices

No body. Returns array of all your devices.

---

#### GET `/api/devices/{id}/` — Get one device

Replace `{id}` with the device UUID.

---

#### PUT `/api/devices/{id}/` — Full update

**Send (both fields required):**
```json
{"name": "New Name", "is_active": true}
```

---

#### PATCH `/api/devices/{id}/` — Partial update

**Send (any field):**
```json
{"is_active": false}
```

---

#### DELETE `/api/devices/{id}/` — Deactivate device

No body. Returns `{"detail": "Device deactivated."}` — data is kept, device is just blocked.

---

### Locations endpoints

---

#### POST `/api/locations/` — Post GPS reading

⚠️ ESP32 only. Use `X-Device-Token` header, NOT JWT.

**Header:** `X-Device-Token: your-64-char-token`

**Send:**
```json
{
    "latitude": "23.726008",
    "longitude": "90.406723",
    "accuracy": 5.0,
    "speed": 1.2,
    "battery_pct": 87
}
```

**Success 201:** Returns saved reading. Also auto-updates `device.last_seen`, `device.battery_pct`, and pushes WebSocket message to dashboard.

---

#### GET `/api/locations/?device={uuid}` — Location history

**Header:** `Authorization: JWT your-access-token`

Returns paginated list (20 per page). Use `&page=2` for next page.

**Success 200:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/locations/?device=uuid&page=2",
    "previous": null,
    "results": [...]
}
```

---

#### GET `/api/locations/{id}/` — Single reading

Returns one LocationReading by its UUID.

---

#### GET `/api/locations/latest/?device={uuid}` — Current position

**Header:** `Authorization: JWT your-access-token`

`?device=` is required. Returns single most recent GPS reading for that device.

**404 if** the device has never sent a GPS reading yet.

---

### Alerts endpoints

---

#### POST `/api/alerts/` — Trigger alert

⚠️ ESP32 only. Use `X-Device-Token` header, NOT JWT.

**Header:** `X-Device-Token: your-64-char-token`

**Send:**
```json
{
    "alert_type": "PANIC",
    "latitude": "23.726008",
    "longitude": "90.406723"
}
```

`alert_type` must be one of: `PANIC`, `GEOFENCE`, `MOTION`

**Success 201:** Saves alert, fires Celery SMS task, pushes WebSocket notification.

---

#### GET `/api/alerts/?device={uuid}` — List alerts

**Header:** `Authorization: JWT your-access-token`

Optional filters:
- `?resolved=false` — active alerts only
- `?resolved=true` — resolved alerts only
- `?alert_type=PANIC` — filter by type

**Success 200:** Paginated list with `alert_type_display` showing human-readable type.

---

#### GET `/api/alerts/{id}/` — Single alert

Full details of one alert by UUID.

---

#### PUT `/api/alerts/{id}/resolve/` — Mark resolved

**Header:** `Authorization: JWT your-access-token`

No body needed. Returns `{"status": "resolved"}`. Sets `resolved=true` on the alert.

---

### Geofences endpoints

All require: `Authorization: JWT your-access-token`

---

#### POST `/api/geofences/` — Create safe zone

**Send:**
```json
{
    "device": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "Home",
    "latitude": "23.726008",
    "longitude": "90.406723",
    "radius_m": 150,
    "is_active": true
}
```

---

#### GET `/api/geofences/?device={uuid}` — List geofences

Optional: `?is_active=true`

---

#### GET `/api/geofences/{id}/` — Single geofence

---

#### PUT `/api/geofences/{id}/` — Full update

All fields required.

---

#### PATCH `/api/geofences/{id}/` — Partial update

Send only what you want to change:
```json
{"radius_m": 300}
```
or
```json
{"is_active": false}
```

---

#### DELETE `/api/geofences/{id}/` — Delete permanently

Returns `204 No Content`. Cannot be undone. Use PATCH `is_active: false` to temporarily disable instead.

---

### WebSocket

**URL:** `ws://localhost:8000/ws/device/{device_id}/`

Connect in JavaScript:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/device/b2c3d4e5-f6a7-8901-bcde-f12345678901/');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'location') {
        console.log('New position:', data.lat, data.lon, data.ts);
        // Update map marker here
    }

    if (data.type === 'alert') {
        console.log('ALERT:', data.alert_type, data.lat, data.lon);
        // Show notification popup here
    }
};
```

Messages you receive:
```json
// GPS update (every time ESP32 posts location)
{"type": "location", "lat": "23.726008", "lon": "90.406723", "ts": "2025-01-15T14:35:00Z"}

// Alert notification (every time ESP32 triggers an alert)
{"type": "alert", "alert_type": "PANIC", "lat": "23.726008", "lon": "90.406723"}
```
