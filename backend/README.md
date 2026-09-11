# Backend — Calorie Tracker API

FastAPI + SQLAlchemy 2 + Alembic. Serves the JSON API **and** the built React
SPA from a single port (`0.0.0.0:8080`).

## Layout

```
backend/
  app/
    main.py                 # FastAPI app, CORS, health, SPA mount
    core/config.py          # env-var configuration
    core/security.py        # bcrypt (passlib) + JWT (python-jose)
    api/deps.py             # get_db, get_current_user (HTTP Bearer)
    api/routes/auth.py      # /auth/register, /auth/login, /auth/me
    api/routes/foods.py     # /foods/search, /foods/{fdcId}
    api/routes/log.py       # /log, /log/daily, /log/history, /log/{id}
    schemas/                # pydantic request/response models
    services/fdc.py         # USDA FoodData Central client (key server-side)
    services/foods.py       # cache-first food resolution + macro scaling
    db/, models/            # database layer (session, queries, ORM models)
  alembic/                  # migrations (run on container startup)
  scripts/run_migrations.sh # wait-for-db + `alembic upgrade head`
  scripts/start.sh          # migrations, then uvicorn on 0.0.0.0:8080
  requirements.txt
```

## Configuration (environment variables)

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | `postgresql+psycopg2://postgres:postgres@db:5432/calorie` | `postgres://`/`postgresql://` are normalized to psycopg2 |
| `JWT_SECRET` | yes (prod) | `dev-insecure-secret-change-me` | HMAC signing key |
| `JWT_ALGORITHM` | no | `HS256` | |
| `JWT_EXPIRES_MINUTES` | no | `10080` (7 days) | |
| `NUTRITION_API_KEY` | yes | — | USDA FDC key; **server-side only**, never returned to the client |
| `FDC_BASE_URL` | no | `https://api.nal.usda.gov/fdc/v1` | |
| `FDC_TIMEOUT_SECONDS` | no | `10` | upstream timeouts surface as `502` |
| `STATIC_DIR` | no | `/app/static` | built React assets |
| `CORS_ORIGINS` | no | `*` | comma separated |
| `HOST` / `PORT` | no | `0.0.0.0` / `8080` | |

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | No | Liveness probe |
| POST | `/auth/register` | No | Register (unique email, bcrypt) → JWT |
| POST | `/auth/login` | No | Login → JWT |
| GET | `/auth/me` | Yes | Current user |
| GET | `/foods/search?q=` | Yes | FDC proxy → `[{fdcId, name, brandOwner}]` |
| GET | `/foods/{fdcId}` | Yes | Per-100g macros, cache-first |
| POST | `/log` | Yes | Log a portion |
| GET | `/log/daily?date=YYYY-MM-DD` | Yes | Day's entries + totals |
| GET | `/log/history?start=&end=` | Yes | Entries grouped by day + per-day totals |
| DELETE | `/log/{id}` | Yes | Delete own entry (404 otherwise) |

All `/foods` and `/log` routes require `Authorization: Bearer <jwt>` and return
`401` when the header is missing, malformed or the token is invalid/expired.

## Behaviour notes

* **FDC key isolation** — `NUTRITION_API_KEY` is read only in
  `app/services/fdc.py` and attached to the outgoing query string. No response
  model contains it; `/health` reports only a boolean.
* **Cache-first** — `GET /foods/{fdcId}` and `POST /log` both call
  `services.foods.resolve_food()`: read `fdc_foods`, and only on a miss call
  FDC (`format=abridged&nutrients=203,204,205,208`), extract nutrients by
  `nutrient.number` (208→kcal, 203→protein, 204→fat, 205→carbs), insert the row
  with `ON CONFLICT DO NOTHING` (rows are never updated) and return it.
* **Write-time macros** — `calories/protein/fat/carbs = (per_100g / 100) *
  portion_grams`, rounded to 2 dp and stored. Reads sum the stored columns and
  never recalculate. `food_name` is snapshotted at log time.
* **`eaten_at` validation** — must parse as a datetime; naive values are treated
  as UTC. Future timestamps and anything older than 365 days are rejected with
  `422`. Omitted → server UTC `now()`.
* **Upstream failures** — timeouts, transport errors, 4xx/5xx from FDC and a
  missing API key all map to `502` with a safe message; an unknown `fdcId`
  maps to `404`.
* **Ownership** — every `/log` query is scoped to the authenticated user;
  deleting somebody else's entry returns `404`, not `403`.
* **SPA** — `StaticFiles` is mounted at `/` with an `index.html` fallback for
  client-side routes; missing files under `assets/` still return `404`.

## Running

```sh
docker compose up --build        # http://127.0.0.1:8080
```

Locally, without Docker:

```sh
pip install -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg2://calorie:calorie@localhost:5432/calorie
export JWT_SECRET=dev NUTRITION_API_KEY=...
cd backend && alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Interactive docs: `http://127.0.0.1:8080/docs`.
