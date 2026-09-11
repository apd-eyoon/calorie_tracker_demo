# Calorie Tracker

A full-stack calorie and macronutrient tracking web application. Users register and sign in with their own account, search the USDA FoodData Central (FDC) database for real foods, and log servings to a daily food diary. Each day's entries roll up into totals for calories, protein, carbohydrates, and fat so users can track progress against their goals. The backend is a FastAPI service backed by PostgreSQL with Alembic-managed migrations; the frontend is a React + TypeScript single-page app.

---

## Prerequisites

**Primary path (recommended):**

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- Docker Compose v2 (`docker compose`)

**Optional (only for running without Docker):**

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+

**External service:**

- A free [USDA FoodData Central API key](https://fdc.nal.usda.gov/api-key-signup.html) for food search.

---

## Quick Start with Docker

```bash
git clone <repo-url>
cd <repo>
cp .env.example .env       # then add your FDC_API_KEY
docker compose up --build
# Open http://localhost:8080
```

> If you are running Docker in a nested/remote environment, use
> `http://host.docker.internal:8080` instead of `localhost`.

On startup the backend container automatically runs `alembic upgrade head` before serving traffic, so the database schema (`users`, `fdc_foods`, `food_log`) is created for you.

To stop and remove everything, including the database volume:

```bash
docker compose down -v
```

---

## Environment Variables

Create a `.env` file in the project root. `.env` is git-ignored.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | `postgresql+psycopg2://postgres:postgres@db:5432/calorie` | SQLAlchemy/Alembic connection URL. `postgres://` and `postgresql://` forms are normalized to `psycopg2` automatically. |
| `POSTGRES_USER` | yes | `postgres` | Postgres superuser for the `db` container. |
| `POSTGRES_PASSWORD` | yes | `postgres` | Postgres password. |
| `POSTGRES_DB` | yes | `calorie` | Database name created on first boot. |
| `SECRET_KEY` | yes | — | Secret used to sign JWT access tokens. Use a long random string. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `60` | Lifetime of issued access tokens. |
| `FDC_API_KEY` | yes | — | USDA FoodData Central API key used by the food search endpoint. |
| `VITE_API_BASE_URL` | no | `/api` | Base URL the frontend uses to reach the API. |

Example `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=calorie
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/calorie
SECRET_KEY=change-me-to-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=60
FDC_API_KEY=your-fdc-api-key
```

---

## Development Setup (without Docker)

### 1. Database

Start a local PostgreSQL instance and create the database:

```bash
createdb calorie
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/calorie"
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="dev-secret"
export FDC_API_KEY="your-fdc-api-key"

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs are then available at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

### Migrations

Run from the `backend/` directory:

```bash
alembic upgrade head                       # apply all migrations
alembic downgrade -1                       # roll back one revision
alembic revision --autogenerate -m "msg"   # create a new revision
```

Alembic reads `DATABASE_URL` from the environment; `sqlalchemy.url` in `alembic.ini` is intentionally blank.

---

## Project Structure

```
.
├── docker-compose.yml          # db + backend + frontend services
├── .env                        # local configuration (git-ignored)
├── backend/
│   ├── alembic.ini             # Alembic config (URL comes from env)
│   ├── alembic/
│   │   ├── env.py              # resolves DATABASE_URL, loads model metadata
│   │   ├── script.py.mako      # migration template
│   │   └── versions/
│   │       └── 0001_initial_schema.py   # users, fdc_foods, food_log
│   ├── app/
│   │   ├── main.py             # FastAPI app and router wiring
│   │   ├── api/                # auth, food search, and food log routes
│   │   ├── core/               # settings, security, JWT helpers
│   │   ├── db/                 # Base metadata and session fact