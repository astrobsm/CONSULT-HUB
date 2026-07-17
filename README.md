# ConsultHUB

Intelligent Multidisciplinary Consultation & Care Coordination Platform.

This repository is an early scaffold. The first implemented vertical slice is the
**consultation workflow** (create → route → acknowledge/accept → recommendations →
complete), including workflow-state tracking and an escalation-ready event log.

## Structure

```
backend/    FastAPI + SQLAlchemy (consultation workflow API)
frontend/   React 19 + Vite + TypeScript (consultation UI)
```

## Backend — quick start

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # creates a demo institution + users
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health:   http://localhost:8000/api/health

**Demo logins** (all password `consulthub`): `superadmin@consulthub.local`
(super admin), `admin@consulthub.local` (institution admin), `registrar@…`,
`consultant@…`.

Dev uses SQLite (`consulthub.db`) out of the box. Set `DATABASE_URL` in `backend/.env`
to point at PostgreSQL for production.

**Schema management:**
- **Dev/tests** auto-create tables on startup (`create_all`) — zero setup.
- **Production** uses Alembic migrations (authoritative). `env.py` reads
  `settings.database_url` and the app's metadata:
  ```bash
  cd backend
  alembic upgrade head            # apply migrations to the configured DB
  alembic revision --autogenerate -m "describe change"   # after model changes
  ```
  SQLite runs migrations in batch mode; the same migrations apply to PostgreSQL.
  The initial migration includes the appointments partial-unique index that
  enforces no double-booking.

### Auth & multi-tenancy

- JWT bearer auth (`POST /api/auth/login`, OAuth2 password flow). `GET /api/auth/me`
  returns the current user; `POST /api/auth/register` creates one.
- Every consultation endpoint requires a token. The institution and requesting
  user are taken from the token — never trusted from the request body — and each
  workflow event records the real actor.
- Consultations are **tenant-scoped**: users only see and act on consultations in
  their own institution (cross-tenant reads return 404).
- `secret_key` MUST be overridden via env in any real deployment. Password hashing
  is PBKDF2-HMAC-SHA256 (stdlib); swap for argon2/bcrypt before production.

### Outpatient appointments (clinic scheduling)

A distinct module from the inpatient consult workflow — see
[docs/clinic-appointment-module.md](docs/clinic-appointment-module.md). An
appointment may link a consultation (`consultation_id`), but booking/slotting is
separate.

- **Clinics & stations** (admin): each clinic has operating days/hours, breaks,
  slot duration and a load-balancing mode; each clinic has unlimited consultation
  stations (typed, with room + assigned clinician + active/inactive/maintenance).
- **Slots** are generated per station from the clinic's hours/duration, skipping
  breaks and non-operating weekdays. `GET /clinics/{id}/availability?date=` returns
  free slots per station (minus booked + held).
- **No double-booking (guaranteed at the DB):** a partial unique index on
  (station, slot) over active statuses — a duplicate is impossible, not merely
  checked. A conflicting booking gets 409 "This appointment slot is no longer
  available."
- **Load balancing:** booking without a station auto-assigns the least-busy free
  station (round-robin configurable), keeping counts within one across stations.
- **Slot holds:** `POST /appointments/hold` reserves a slot for a few minutes
  (`APPOINTMENT_HOLD_MINUTES`) while a booking completes; held slots drop out of
  availability and expire automatically.
- **Lifecycle:** `POST /appointments/{id}/transition` walks booked → confirmed →
  checked-in (assigns a queue position) → called → in-progress → completed, plus
  did-not-attend / cancelled / rescheduled (a cancel frees the slot for rebooking).
- UI: an **Appointments** page (book: patient → clinic → date → type → pick a time;
  and a filterable clinic list/queue with lifecycle actions), plus a **Clinics** tab
  in Admin to manage clinics and stations.
- **Waiting list:** when a day is full, `POST /clinics/{id}/waiting-list` adds a
  patient; cancelling an appointment **auto-promotes** the oldest waiting patient
  into the freed slot (via the same booking path) and links the new appointment.
- **QR check-in:** each booking gets a `check_in_code`; `GET /appointments/{id}/qrcode`
  returns an SVG QR (segno, no image deps); reception scans/enters it at
  `POST /appointments/check-in` to check the patient in and assign a queue number.
- **Reminders:** a background job (`REMINDER_INTERVAL_SECONDS`) sends reminders at
  7d / 3d / 24h / 2h / 30m before each appointment — each offset once, the tightest
  crossed bucket fires, logged in `appointment_reminders` and delivered as in-app
  notifications to the booker and assigned clinician. The core `run_reminders(now)`
  is a pure, deterministically testable function.
- UI: a QR modal + reception "check-in by code" bar + waiting-list panel on the
  Appointments page.

### Administration & RBAC

- **Self-registration is disabled.** Admins create users via `POST /api/users`;
  the first admin comes from the seed script. Roles are defined in
  `app/core/roles.py` (17 roles); `GET /api/users/roles` lists them.
- **Admin tiers:** `super_admin` (cross-tenant) and `institution_admin`
  (own institution). `require_admin` gates the admin surface.
- **User management** (`/api/users`): list / create / get / update
  (role, department, active). Guards enforced: non-super admins are scoped to
  their own institution (cross-tenant reads 404), only a super admin may grant
  `super_admin`, and you cannot deactivate your own account.
- **Org management:** `/api/institutions` (super admin creates tenants; others
  see only their own) and `/api/departments` (list / create / rename, tenant-scoped).
- UI: an **Admin** section (visible only to admins) with Users and Departments
  tabs — create users, change roles/department inline, activate/deactivate, and
  manage departments. Escalation recipient roles (consultant / HOD / MD) are now
  real users you can assign here.

### Patients

- Tenant-scoped patient registry: `POST /api/patients`, `GET /api/patients`
  (with `?search=` over name / hospital number), `GET /api/patients/{id}`.
- `age` and `bmi` are computed server-side and returned read-only.
- Consultations can link a patient (`patient_id`); the API rejects references to
  patients outside the caller's institution (422). List consultations for a
  patient with `GET /api/consultations?patient_id={id}`.
- UI: patient list + search, registration form, and a patient detail page showing
  demographics and that patient's consultations, plus a one-click "new consult for
  this patient" flow.

### Dashboard

- `GET /api/dashboard/summary` (tenant-scoped) returns operational KPIs: pending /
  today / completed / overdue counts, completion rate, average acknowledgement and
  completion time, pending-by-priority, a status breakdown, and top specialties.
- Overdue = an unacknowledged consult whose elapsed time exceeds its
  `required_response_minutes`.
- UI is the landing page: KPI tiles + horizontal breakdown bars. Colors come from
  the validated data-viz reference palette (reserved status hues for priority,
  single sequential hue for magnitude), theme-aware for light/dark.
- Note: metrics aggregate in Python at dev scale; move to SQL `GROUP BY` / a rollup
  before large tenants.

### Escalation engine

- A background scheduler (APScheduler, in-process) periodically scans
  unacknowledged, non-terminal consultations and fires every escalation threshold
  each has crossed. Default policy (spec): **15 / 30 / 60 / 90 / 120 min** →
  reminder, second reminder, consultant, HOD, Medical Director.
- Each crossing writes an auditable `EscalationEvent` (and a consultation event);
  the consultation's `escalation_level` tracks the highest level reached.
  Acknowledging a consult stops further escalation.
- The core is a pure function `run_escalations(db, now)` — deterministically
  testable by injecting `now`. Notification delivery is a logging stub
  (`_notify`) — wire it to push/SMS/email/WhatsApp later.
- `GET /api/escalation/policy` returns the configured steps. Toggle/pace the engine
  with `ESCALATION_ENABLED` / `ESCALATION_INTERVAL_SECONDS`.
- UI: escalation badge on consult lists + a per-consult escalation history; the
  dashboard shows an "Escalated" KPI.
- **Scaling note:** in-process APScheduler runs per web process — with multiple
  workers, move the job to a single scheduler process or Celery Beat + Redis (per
  the spec) so escalations don't run N times.

### Notifications

- In-app notifications persisted per user: `GET /api/notifications`
  (`?unread_only=`), `GET /api/notifications/unread-count`,
  `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all`.
- Emitted by domain events via `app/services/notifications.py`:
  - **Escalation** → notifies the requester at every level, plus senior roles
    (consultant / admins as HOD / Medical Director proxies) from level 3.
  - **Status change** → in-app notifies the requester when their consult is
    acknowledged / accepted / seen / completed / rejected / returned (never the
    actor themselves).
- **Email transport** (`app/core/email.py`): sends via SMTP when `SMTP_HOST` is
  configured, otherwise logs to the console — best-effort, never breaks a request
  or escalation run. Escalations send email; status changes are in-app only for
  now (queue them before enabling high-volume email).
- UI: a header bell with a live unread badge (polls every 20s) and a dropdown that
  lists notifications, marks them read, and deep-links to the consultation.

### Attachments

- Files attach to a consultation: `POST /api/consultations/{id}/attachments`
  (multipart), `GET /api/consultations/{id}/attachments`,
  `GET /api/attachments/{id}/download`, `DELETE /api/attachments/{id}`.
- Tenant-scoped (cross-tenant access 404); size-limited (`MAX_UPLOAD_MB`, 413 over
  limit); delete allowed for the uploader or an admin.
- **Storage** (`app/core/storage.py`): `LocalStorage` writes to `STORAGE_DIR` with
  a small save/path/delete interface — swap the `storage` instance for an
  S3-compatible backend without touching callers. Keys are random UUIDs
  (traversal-safe); originals are preserved as the download filename.
- UI: an attachments panel on the consult detail page — pick a file to upload,
  list attachments with size/type, download (authenticated fetch → blob), delete.
  Downloads use an auth header (not a bare link), so files stay access-controlled.

### Secure discussion (per-consultation chat)

- Threaded messages on a consultation: `GET /api/consultations/{id}/messages`,
  `POST /api/consultations/{id}/messages` — tenant-scoped (cross-tenant 404).
- Posting a message notifies the requester and prior thread participants (never
  the sender) via the in-app notification system.
- UI: a discussion panel on the consult detail page (own messages right-aligned,
  Enter to send, polls every 15s for new messages).

### FHIR R4 export

- Read-only FHIR R4 API under `/api/fhir` (served as `application/fhir+json`,
  tenant-scoped, auth required):
  - `GET /fhir/metadata` — CapabilityStatement.
  - `GET /fhir/Patient/{id}` and `GET /fhir/Patient?name=|identifier=` — a Patient
    resource / searchset Bundle.
  - `GET /fhir/ServiceRequest/{id}` and `GET /fhir/ServiceRequest?patient=` — a
    consultation as a ServiceRequest / searchset Bundle.
  - `GET /fhir/Patient/{id}/$everything` — a Bundle with the Patient and their
    ServiceRequests.
- Mapping (`app/fhir/mappers.py`): Consultation → **ServiceRequest** (status →
  draft/active/on-hold/completed/revoked, priority routine/urgent/emergency →
  routine/urgent/stat); Patient → **Patient** (hospital number as identifier,
  name split, sex → gender, DOB, phone). Hand-built valid R4 JSON — no FHIR
  library dependency.
- UI: a FHIR export panel on the patient detail page — view the `$everything`
  Bundle and download it as `.json`.

### Real-time push (WebSockets)

- Authenticated channel at `WS /api/ws?token=<jwt>` (token in the query string
  since browsers can't set headers on the WS handshake). Invalid token → close
  1008.
- `app/core/realtime.py` holds a per-user connection registry and a thread-safe
  `publish()` that schedules the send on the main event loop via
  `run_coroutine_threadsafe` — so synchronous routes **and** the background
  escalation thread can push. Events are published **after** the DB commit, so a
  client that refetches on the event sees committed data.
- Events: `{"type":"notification"}` (a new notification for you → refresh the
  bell) and `{"type":"message","consultation_id":N}` (a new chat message → refresh
  that thread). The frontend `RealtimeBridge` connects, invalidates the matching
  queries, and reconnects with backoff; the bell/chat keep a slow 60s poll only as
  a fallback.
- Uvicorn needs a WS implementation — `websockets` is in requirements. In dev the
  Vite proxy forwards the upgrade (`ws: true`).

### Account self-service

- `PATCH /api/auth/me` edits the caller's own profile (full name, designation);
  role and institution remain admin-controlled.
- `POST /api/auth/change-password` verifies the current password before setting a
  new one. UI: an Account page (linked from the header name) with profile and
  change-password forms.

### Password reset & email invites

- **Forgot password:** `POST /api/auth/password-reset/request` always returns 202
  (no account enumeration); if the email is a known active user, a short-lived
  reset token is emailed as a `/set-password?token=…` link.
- **Set password:** `POST /api/auth/password-reset/confirm` validates the token
  (purpose-checked: an access token can't be used as a reset) and sets the new
  password; also used to accept invites.
- **Admin invites:** `POST /api/users/invite` (admin) creates a user with an
  unusable placeholder password and emails a set-password link (7-day token). The
  invitee can't log in until they set a password.
- **Dev:** with no SMTP configured, emails (including the reset/invite link) are
  logged to the backend console. Set `SMTP_*` for real delivery and
  `FRONTEND_BASE_URL` for the link host.
- UI: a "Forgot password?" link on sign-in → Forgot-password page; a public
  Set-password page reads the token from the URL; the Admin > Users form has a
  "send email invite" toggle.

### Continuous integration

`.github/workflows/ci.yml` runs the backend pytest suite (Python 3.12) and the
frontend build (Node 20) on every push and pull request.

## Frontend — quick start

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173 (proxies `/api` to the backend on :8000)

## Tests

```bash
cd backend
.venv\Scripts\python.exe -m pytest      # 41 tests, ~20s
```

Each test runs against a freshly seeded, isolated SQLite database (see
`tests/conftest.py`). Coverage spans auth, RBAC + tenant isolation, the
consultation workflow and escalation engine, patients, notifications, secure
chat, attachments, FHIR export, and the appointment module (no-double-book,
even load distribution, holds, lifecycle, reschedule). `PBKDF2_ITERATIONS` is
lowered in tests for speed.

## Roadmap

The full spec covers multi-tenant auth/RBAC, patient registration, AI assist,
FHIR/HL7 interop, offline-first sync, notifications, and analytics. This scaffold
establishes the domain model and workflow engine those modules build on.
