# Familienfelsen – Technical Roadmap to V1.0

## Goal

Build a simple, portable and self-hosted web application for discovering and contributing family-friendly climbing crags.
The application should prioritize **search, filtering and useful family information** over maps or complex social features.

### Core principles

* Simple server-rendered architecture
* Mobile-first UI
* PostgreSQL as the source of truth
* Community-contributed content
* Docker-native deployment
* No vendor lock-in
* Minimal JavaScript
* Build functionality incrementally

---

# Technical Stack

| Component           | Technology                  |
| ------------------- | --------------------------- |
| Application         | Python / Django             |
| Frontend            | Django Templates + PicoCSS  |
| Database            | PostgreSQL                  |
| Authentication      | Django Auth                 |
| Administration      | Django Admin                |
| Image processing    | Pillow                      |
| Application Server  | Gunicorn                    |
| Reverse Proxy       | Caddy/Traefik               |
| Deployment          | Docker Compose              |
| Persistent Storage  | Docker Volumes              |

### Architecture

Browser >> HTTPS >> reverse Proxy >> Django + Gunicorn >> PostgreSQL

Persistent volumes:
- postgres_data
- media

---

# V0.1 – Foundation & Data Model

### Goal

A working database-backed Django application running entirely through Docker Compose.

### Features

* Django project
* PostgreSQL
* Docker Compose
* Django Admin
* Initial database schema
* Database migrations
* Seed/test data

### Initial entities

```text
Area
Crag
Photo
```

Core `Crag` structure:

```text
Crag
├── name
├── area
├── description
├── orientation
├── family_rating
```

### Definition of Done

```bash
docker compose up -d
```

starts the complete environment.

Django Admin allows creation/editing of Areas, Guidebooks and Crags.

Database contains approximately 5 realistic test crags.

---

# V0.2 – Public Search & Filtering

### Goal

Deliver the application's primary value proposition: **finding suitable crags quickly**.

### Features

Public crag list with:

* Free-text search
* Area filter
* Family rating filter

Filters use standard URL query parameters: This makes searches bookmarkable and shareable.

### UI

```text
Find a crag

[ Search........................ ]

[ Area ▼ ][ Family Rating ▼ ]

--------------------------------------

Sonnenwand
Allgäu · Allgäu Rock

★★★★☆
SW · 15 min approach

[ View details ]
```

### Definition of Done

An anonymous visitor can search and filter the test dataset without authentication.

---

# V0.3 – Crag Detail Pages

### Goal

Provide all relevant information required for a family to evaluate a crag.

### Features

Individual page:

```text
/crags/<slug>/
```

Displays:

* Name
* Area
* Family rating
* Description
* Orientation
* Approach
* Stroller suitability
* Photos


### Design

Mobile-first, simple and content-focused:


### Definition of Done

The public read-only application is useful without requiring an account.

This is the first version to test with real users.

---

# V0.4 – Users & Authentication

### Goal

Turn the read-only database into a community application.

### Features

* Custom Django User model
* Registration
* Login
* Logout
* Password reset
* Session-based authentication
* User profile
* Roles/permissions

Initial roles:

```text
USER
ADMIN
```

Relationships:

```text
User
  │
  ├── creates → Crag
  │
  └── uploads → Photo
```

### Authorization

Anonymous:

```text
READ
SEARCH
FILTER
```

Authenticated user:

```text
CREATE crag
EDIT own crag
UPLOAD photo
DELETE own photo
```

Admin:

```text
EDIT all
DELETE all
MODERATE
```

All authorization checks are performed server-side.

### Definition of Done

A user can register, authenticate and maintain a persistent secure session.

---

# V0.5 – Community Contributions

### Goal

Allow authenticated users to contribute crags.

### Features

**Add Crag** workflow:

```text
Basic information
       ↓
Family suitability
       ↓
Location
       ↓
Guidebooks
       ↓
Review
       ↓
Submit
```

Django Forms provide:

* server-side validation
* CSRF protection
* error handling
* database persistence

Users can:

```text
Create own crag
View own submissions
Edit own crag
Submit for publication
```

Lifecycle:

```text
DRAFT
   ↓
PENDING
   ↓
PUBLISHED

or

REJECTED
```

### Definition of Done

A normal registered user can create a complete crag entry without accessing Django Admin.

---

# V0.6 – Photo Uploads

### Goal

Allow families to visually assess the location.

### Photo categories

```text
CRAG
BASE_AREA
APPROACH
PARKING
OTHER
```

### Upload pipeline

```text
Browser
   │
   │ multipart/form-data
   ▼
Django
   │
   ├── authenticate
   ├── validate MIME/type
   ├── validate size
   ├── generate safe filename
   │
   ▼
Pillow
   │
   ├── resize
   ├── re-encode
   ├── optimize
   └── remove EXIF
   │
   ▼
media volume
```

PostgreSQL stores metadata; image binaries remain in storage.

Later extensions can include HEIC support and migration to S3-compatible object storage.

### Definition of Done

Authenticated users can upload photos to their own crags and the images appear on public detail pages.

---

# V0.7 – Moderation & Administration

### Goal

Make community-generated content manageable.

Use **Django Admin** rather than building a custom moderation application.

### Admin capabilities

* Review pending crags
* Publish/reject submissions
* Edit incorrect information
* Manage users
* Manage Areas
* Manage Guidebooks
* Remove inappropriate photos/content

Workflow:

```text
User submission
       ↓
    PENDING
       ↓
  Django Admin
       │
   ┌───┴────┐
   ▼        ▼
PUBLISH   REJECT
   │
   ▼
Public
```

### Definition of Done

New community content can be reviewed and controlled without database access or custom administrative tooling.

---

# V0.8 – UX & Mobile Polish

### Goal

Make the application pleasant to use on a phone at home or at the crag.

Focus on:

* Responsive layout
* Clear typography
* Accessible forms
* Large touch targets
* Fast search/filter workflow
* Useful empty states
* Form validation feedback
* Image gallery
* Navigation
* Basic accessibility
* Performance

Technology remains:

```text
HTML
CSS
Django Templates
```

JavaScript is introduced only where it solves a concrete UX problem.

**htmx remains optional.**

---

# V0.9 – Production Hardening

### Goal

Prepare the application for public deployment.

### Security

* HTTPS through Caddy
* Secure cookies
* CSRF protection
* production `SECRET_KEY`
* credentials through environment/secrets
* restricted upload types
* upload size limits
* rate limiting where appropriate
* production logging
* `manage.py check --deploy`

### Persistence

```text
PostgreSQL
    ↓
scheduled pg_dump
    ↓
external backup


/media
    ↓
scheduled backup
    ↓
external backup
```

A backup is only considered working once a **restore has been tested**.

### Operations

Add:

* health checks
* container restart policies
* structured/logical logging
* database migration process
* deployment documentation
* `.env.example`
* upgrade procedure
* restore procedure

### Definition of Done

The application can safely run on a public Docker host and can be recovered from backup.

---

# V1.0 – First Public Release

V1.0 is deliberately small.

A visitor can:

```text
Search
  ↓
Filter
  ↓
Discover crag
  ↓
Evaluate family suitability
  ↓
View photos
  ↓
Open rock/parking location
```

A community member can:

```text
Register / Login
       ↓
Add crag
       ↓
Add family information
       ↓
Add guidebook references
       ↓
Upload photos
       ↓
Submit
```

An administrator can:

```text
Review
Publish
Correct
Moderate
Manage
```

### V1.0 Scope

✓ Search and filters
✓ Crag detail pages
✓ PostgreSQL + JSONB
✓ Areas and guidebooks
✓ User accounts
✓ Community submissions
✓ Ownership/permissions
✓ Photo uploads
✓ Moderation
✓ Mobile-first UI
✓ Docker deployment
✓ HTTPS
✓ Backups and tested restore

### Explicitly NOT V1.0

✗ Interactive map
✗ Native mobile app
✗ Comments
✗ Community reputation system
✗ Elasticsearch/OpenSearch
