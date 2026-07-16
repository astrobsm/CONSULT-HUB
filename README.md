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
to point at PostgreSQL for production. Tables are auto-created on startup; wire up
Alembic migrations before production.

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

## Frontend — quick start

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173 (proxies `/api` to the backend on :8000)

## Roadmap

The full spec covers multi-tenant auth/RBAC, patient registration, AI assist,
FHIR/HL7 interop, offline-first sync, notifications, and analytics. This scaffold
establishes the domain model and workflow engine those modules build on.
