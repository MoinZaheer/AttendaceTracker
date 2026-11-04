# 🏗️ Architecture

## System Overview

Sentinel is a 4-tier architecture deployed as Docker containers behind an Nginx reverse proxy.

```
                    ┌─────────────────────────────────────────────────┐
                    │                 INTERNET                        │
                    └──────────────────┬──────────────────────────────┘
                                       │ HTTPS :443
                    ┌──────────────────▼──────────────────────────────┐
                    │              Nginx (Alpine)                     │
                    │  • TLS termination (Let's Encrypt)              │
                    │  • Rate limiting (5r/m login, 100r/m API)       │
                    │  • Gzip compression (level 4)                   │
                    │  • Static file serving (/frontend/*)            │
                    │  • Proxy pass → FastAPI :8000                   │
                    └──────┬──────────────────────┬───────────────────┘
                           │ /api/v1/*            │ /*.html, /css, /js
                    ┌──────▼──────────┐    ┌──────▼───────────┐
                    │   FastAPI App   │    │  Static Files    │
                    │   (Uvicorn)     │    │  (Nginx direct)  │
                    │   :8000         │    └──────────────────┘
                    │                 │
                    │  ┌───────────┐  │
                    │  │ Endpoints │  │
                    │  │ auth.py   │  │
                    │  │ employees │  │
                    │  │ reports   │  │
                    │  └─────┬─────┘  │
                    │        │        │
                    │  ┌─────▼─────┐  │
                    │  │  Service  │  │
                    │  │  Layer    │  │
                    │  │ (deps.py) │  │
                    │  └──┬────┬───┘  │
                    └─────┼────┼──────┘
                          │    │
               ┌──────────▼┐  ┌▼──────────┐
               │ PostgreSQL │  │  Redis 7   │
               │    16      │  │  (cache)   │
               │  (asyncpg) │  │ 15s TTL    │
               │  :5432     │  │ :6379      │
               └────────────┘  └────────────┘
```

---

## Component Architecture

### Backend (FastAPI)

```
app/
├── main.py                    # App factory, lifespan, exception handlers
├── api/v1/
│   ├── api.py                 # Router aggregation
│   ├── deps.py                # Dependency injection (DB session, auth)
│   └── endpoints/
│       ├── auth.py            # Login, refresh, logout, user mgmt
│       ├── employees.py       # RFID scan, employee CRUD, breaks
│       └── reports.py         # Reports, analytics, CSV export
├── core/
│   ├── config.py              # pydantic-settings (env vars → typed config)
│   ├── security.py            # JWT create/verify, bcrypt hash/verify
│   └── exceptions.py          # Global HTTPException handlers
├── models/
│   ├── user.py                # User ORM (admin accounts)
│   ├── employee.py            # Employee ORM (RFID card holders)
│   └── attendance.py          # AttendanceEvent ORM
├── schemas/
│   ├── user.py                # User request/response schemas
│   ├── employee.py            # Employee schemas
│   └── attendance.py          # Attendance + report schemas
└── db/
    ├── base.py                # DeclarativeBase
    └── session.py             # AsyncSession factory
```

### Frontend (Vanilla JS)

```
frontend/
├── index.html                 # Kiosk — RFID scan interface
├── login.html                 # Admin login page
├── admin.html                 # Dashboard with live stats
├── employees.html             # Employee CRUD management
├── register.html              # New employee registration
├── reports.html               # Reports & analytics
├── settings.html              # System configuration
├── css/
│   └── main.css               # 1,100+ line design system
└── js/
    ├── script.js              # Kiosk logic (RFID capture, scan processing)
    ├── auth.js                # Auth guard, token refresh, fetch wrapper
    ├── layout.js              # Sidebar, header, page transitions
    └── toast.js               # Global notification system
```

---

## Data Flow

### RFID Scan Flow

```mermaid
sequenceDiagram
    participant Card as RFID Card
    participant Reader as USB Reader
    participant Browser as Kiosk Browser
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Cache as Redis

    Card->>Reader: Tap (125kHz EM4100)
    Reader->>Browser: Keyboard emulation (card UID + Enter)
    Browser->>API: POST /api/v1/scan {uid, type}
    API->>DB: SELECT...FOR UPDATE (row lock)
    alt Card registered
        API->>DB: INSERT AttendanceEvent (IN/OUT toggle)
        API->>Browser: 200 {employee_name, event_type, timestamp}
        Browser->>Browser: Show success toast + update UI
    else Card unknown
        API->>DB: INSERT Employee (auto-register)
        API->>DB: INSERT AttendanceEvent (first IN)
        API->>Browser: 201 {new employee, event_type: IN}
    end
    API->>Cache: Invalidate live_stats cache
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant Browser
    participant API as FastAPI
    participant DB as PostgreSQL

    Browser->>API: POST /auth/login {email, password}
    API->>DB: SELECT User WHERE email = ?
    API->>API: bcrypt.verify(password, hash)
    alt Valid credentials
        API->>Browser: Set-Cookie: access_token (HttpOnly, 30min)
        API->>Browser: Set-Cookie: refresh_token (HttpOnly, 7d)
        Browser->>Browser: localStorage.setItem(isLoggedIn, true)
    else Invalid
        API->>Browser: 401 Unauthorized
    end

    Note over Browser,API: On subsequent requests
    Browser->>API: GET /api/v1/... (Cookie: access_token)
    API->>API: JWT decode + verify
    alt Token valid
        API->>Browser: 200 + response data
    else Token expired
        Browser->>API: POST /auth/refresh (Cookie: refresh_token)
        API->>Browser: New access_token cookie
    end
```

---

## Database Schema

```mermaid
erDiagram
    USERS {
        int id PK
        string email UK
        string hashed_password
        string role "admin | user"
        boolean is_active
        datetime created_at
    }

    EMPLOYEES {
        int id PK
        string uid UK "RFID card UID"
        string name
        string email
        string department
        string position
        string phone
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    ATTENDANCE_EVENTS {
        int id PK
        int employee_id FK
        string event_type "IN | OUT | BREAK_START | BREAK_END"
        datetime timestamp
        string uid "RFID card UID"
    }

    ATTENDANCE_SETTINGS {
        int id PK
        time work_start "e.g. 09:00"
        time work_end "e.g. 17:00"
        int grace_minutes "e.g. 15"
        string timezone_name "e.g. Europe/London"
        string timezone_offset "legacy compatibility"
    }

    EMPLOYEES ||--o{ ATTENDANCE_EVENTS : "has many"
```

---

## Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.12 | Async support, FastAPI ecosystem, rapid development |
| **Framework** | FastAPI | Async-native, auto-generated OpenAPI docs, Pydantic validation |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, type-safe, excellent PostgreSQL support |
| **Database** | PostgreSQL 16 | Row-level locking, JSONB, reliability, free |
| **Cache** | Redis 7 | Sub-millisecond reads, TTL support, pub/sub ready |
| **Proxy** | Nginx | Rate limiting, gzip, TLS, static files, battle-tested |
| **Auth** | JWT (HttpOnly cookies) | Stateless, no CSRF for same-site, XSS-resistant |
| **Frontend** | Vanilla JS | Zero build step, instant load, no framework overhead |
| **Container** | Docker Compose | Reproducible deploys, service isolation, easy scaling |
| **RFID** | 125kHz EM4100 USB HID | $6 readers, no drivers, keyboard emulation mode |

---

## Scalability Considerations

### Current Capacity (Single Server)

| Metric | Capacity |
|--------|----------|
| Concurrent users | ~500 |
| Scans per second | ~100 |
| Database size (1 year, 500 employees) | ~500 MB |
| Response time (p95) | <50ms |

### Scaling Path

1. **Vertical:** Increase server CPU/RAM (handles up to ~2,000 employees)
2. **Read replicas:** PostgreSQL streaming replication for report queries
3. **Redis cluster:** For multi-location cache synchronization
4. **Horizontal:** Multiple FastAPI workers behind Nginx load balancer
5. **CDN:** Cloudflare/CloudFront for static assets

---

[← Back to README](README.md)
