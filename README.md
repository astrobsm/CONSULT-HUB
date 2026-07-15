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

**Demo login:** `admin@consulthub.local` / `consulthub` (also a `registrar@…`).

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
