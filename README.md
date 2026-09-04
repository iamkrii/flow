# 🌸 Flow — Period Tracker

A fully functional period & cycle tracking web app.
**Backend:** Flask · **DB:** Oracle Cloud (Autonomous) or SQLite (zero-config dev) · **Frontend:** React (Vite).

## Quick start (one script)

From the project root:

- **Linux / macOS:** `./run.sh`
- **Windows:** double-click `run.bat` (or run it in Command Prompt)

The script builds the frontend and starts the server at http://localhost:8000.

## Features

- 🔐 Email/password auth (JWT tokens, bcrypt hashing)
- 🩸 Period logging with start/end dates, flow level, notes (full CRUD)
- 📅 Calendar view with logged periods, **predicted** future periods, fertile window & ovulation day
- ⭕ Home dashboard: cycle-day ring, current phase (menstrual/follicular/ovulation/luteal), next-period countdown
- 🤒 Symptom tracking (12 presets, severity 1–5)
- 💭 Mood + energy tracking
- 📋 Daily log: weight, BBT temperature, cervical discharge, cramps, intercourse, medication, notes
- 🕓 Unified history timeline with search + delete
- 📊 Insights: cycle-length trend chart (canvas), top symptoms, mood distribution, averages
- ⚙️ Settings: cycle/period/luteal lengths, birth control, reminders; late-period pregnancy hint; JSON data export

## Architecture

### Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | React 18 + Vite, Recharts, Phosphor icons | UI, charts, calendar |
| Backend | Flask (Python) + Pydantic | REST API, validation, predictions |
| Auth | bcrypt + PyJWT | password hashing, token sessions |
| Database | SQLite fallback / Oracle Autonomous (prod) | persistence |
| Oracle ORM | Flask-SQLAlchemy + python-oracledb | Oracle models, sessions, CRUD, reports |

### Project structure

```
├── backend/
│   ├── main.py        # app entry: routes, static serving, SPA fallback
│   ├── cycle.py       # pure logic: averages, predictions, phases, day tagging
│   ├── database.py    # selects exactly one database backend
│   ├── database_sqlite.py  # temporary SQLite fallback and shared-schema adapter
│   ├── database_oracle.py  # Oracle ORM models and SQLAlchemy data access
│   ├── auth.py        # hashing, JWT issue/verify, "current user" dependency
│   └── config.py      # reads env vars (DB_MODE, ORACLE_*, JWT_SECRET)
└── frontend/
    └── src/
        ├── App.jsx            # session gate + tab state + shared data loading
        ├── api.js             # fetch wrapper, auto-attaches Bearer token
        ├── pages/             # one component per screen (Dashboard, Calendar…)
        └── components/        # Sidebar, CalendarCells, CycleCharts, Skeletons…
```

### Request lifecycle

Every call follows the same path:

```
React page → api.js (adds Authorization: Bearer <jwt>)
           → Flask route (Pydantic validates the JSON body)
           → get_current_user_id() decodes the token → user_id
           → selected database backend runs user-scoped data access
           → rows returned as plain JSON
```

- **Tokens:** on login/signup the server returns a JWT (30-day expiry, signed with `JWT_SECRET`). The frontend stores it in `localStorage`; `api.js` attaches it to every request and logs out automatically on a `401`.
- **Passwords** are never stored — only a bcrypt hash. Login = `bcrypt.verify(input, hash)`.
- **Isolation:** every query filters `WHERE user_id = :uid`, so accounts can't see each other's data.

### Database layer

`database.py` is only a backend selector. It imports either `database_sqlite.py`
or `database_oracle.py`, never both data-access implementations at runtime.

- `DB_MODE=sqlite` (default) → thread-local `sqlite3` connections, zero setup,
  with the file at `backend/flow.db`. SQLite reads `sql/oracle_schema.sql` and
  applies a small Oracle-to-SQLite type/default translation because that is the
  temporary local fallback.
- `DB_MODE=oracle` → `database_oracle.py` configures Flask-SQLAlchemy with the
  `oracle+oracledb` dialect. Its ORM models represent all six tables, and its
  ORM session handles CRUD, aggregates, joins, and report queries. The
  `ORACLE_DB_*` environment variables configure the DSN or host/port/service;
  an optional wallet is supported for mTLS.
- `sql/oracle_schema.sql` remains the Oracle SQL script for manual database
  setup and submission. For normal Oracle startup, SQLAlchemy's metadata
  creates only missing tables and indexes.
- Numeric settings are normalized by each backend; `cycle.py` also coerces
  them to ints before doing date math.

### Tables

| Table | Key columns |
|---|---|
| `users` | id, email (unique), password_hash, name |
| `settings` | user_id (PK/FK), avg_cycle_length, avg_period_length, luteal_phase_length, birth_control |
| `periods` | id, user_id FK, start_date, end_date, flow_level (0–3), notes |
| `symptoms` | id, user_id FK, log_date, symptom, severity (1–5) |
| `moods` | id, user_id FK, log_date, mood, energy (1–5) |
| `daily_logs` | id, user_id FK, log_date, weight_kg, temperature_c, discharge, intercourse, medication, cramps |

### Prediction engine (`cycle.py`)

Pure functions — no DB access, easy to unit-test:

1. Sort unique period start dates; gaps between consecutive starts = completed cycles (keep 15–60 day gaps as physiologically valid).
2. `avg_cycle = round(mean(gaps))`, falling back to your Settings value when < 2 cycles exist. Same idea for average period length.
3. `predicted_next = last_period_start + avg_cycle days`
4. `ovulation = predicted_next − luteal_days` (Settings default 14); fertile window = ovulation −5 … +1.
5. Phase today: menstrual (≤ avg period length), follicular, ovulation window (±2 d around ovulation), else luteal.
6. `/api/calendar/{y}/{m}` tags each day: logged period (start→end, filling open-ended ones with the average length), predicted future periods (projected ~6 cycles ahead), fertile, ovulation.

Worked example: starts Jul 25 → Aug 21 gives one 27-day gap → avg 27 → next predicted Sep 17, ovulation Sep 3, fertile Aug 29–Sep 4.

### Frontend architecture

- `App.jsx` owns session state and loads shared data once (`overview` + `periods` via `refreshAll()`), passing it down as props. Screens that mutate data call `refreshAll()` after saving, so every view stays consistent without a global store.
- Routing uses the browser History API: app screens plus `/login` and `/signup` have their own URLs while navigation remains client-side, and Flask's SPA fallback supports direct links and refreshes.
- `CycleCharts.jsx` renders the orange ghost-bar cycle chart and mood donut with Recharts; the calendar is hand-rolled (`CalendarCells`) because the day-tag styling is domain-specific.
- Loading states are skeleton components shaped like their real counterparts (`Skeletons.jsx`); failures render error states with retry — nothing spins forever.
- Build pipeline: `npm run build` = ESLint (flat config, react-hooks rules on) then `vite build` → static assets in `frontend/dist`. Flask serves `/assets` from there and returns `index.html` for any unknown non-API GET, so deep links work. In dev, `npm run dev` serves on :5173 and proxies `/api` to :8000.

## Run it

### Local dev (SQLite — no setup)

```bash
cd flow/backend
python3.12 -m pip install -r requirements.txt
cd ..   # repo root /flow so `backend` package resolves
python3 -m flask --app backend.main run --debug --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

### Production (Oracle Cloud Autonomous DB)

1. Provision an Autonomous Database and download the wallet (if using mTLS).
2. Set environment variables:

```bash
export DB_MODE=oracle
export ORACLE_DB_USER=admin
export ORACLE_DB_PASSWORD='...'
export ORACLE_DB_DSN='yourdb_tp.adb.eu-frankfurt-1.oraclecloud.com:1522/yourservice_tp.adb.oraclecloud.com'
# if using a wallet:
export ORACLE_DB_WALLET_DIR=/path/to/wallet
export ORACLE_DB_WALLET_PASSWORD='...'
export JWT_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))")
```

3. Start as above. Flask-SQLAlchemy creates missing tables and indexes on first
   boot (`users`, `periods`, `symptoms`, `moods`, `daily_logs`, `settings`).

## API summary (`/api` prefix)

| Method | Path | Purpose |
|---|---|---|
| POST | /auth/signup, /auth/login | auth |
| GET | /me | profile + settings |
| PUT | /settings | update cycle settings |
| CRUD | /periods, /symptoms, /moods, /daily | logs |
| GET | /overview | predictions, phase, insights, stats |
| GET | /calendar/{year}/{month} | day classification |
| GET | /history | everything grouped by date |

## Notes

- Predictions use the average of completed cycles (clamped 15–60 days) and fall back to your configured cycle length; ovulation = next period − luteal phase; fertile window = ovulation −5 … +1 days.
- This is a wellness tool, not a contraceptive or medical device.
