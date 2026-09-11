# Database layer

PostgreSQL 16 + SQLAlchemy 2.x ORM + Alembic migrations.

## Layout

```
backend/
  alembic.ini                     # script_location=alembic, URL comes from env.py
  alembic/
    env.py                        # reads DATABASE_URL, target_metadata = Base.metadata
    versions/0001_initial_schema.py
  app/
    db/base.py                    # DeclarativeBase + naming convention
    db/session.py                 # engine, SessionLocal, get_db() dependency
    db/queries.py                 # reusable query helpers
    models/{user,fdc_food,food_log}.py
  scripts/run_migrations.sh       # wait-for-db + `alembic upgrade head`
```

## Configuration

`DATABASE_URL` is the only required variable, e.g.
`postgresql+psycopg2://postgres:postgres@db:5432/calorie`.
`postgres://` / `postgresql://` forms are normalized to the `psycopg2` driver.

## Schema

`users`
| column | type | notes |
| --- | --- | --- |
| id | UUID PK | default `gen_random_uuid()` (also `uuid4` client-side) |
| email | VARCHAR(255) NOT NULL | unique index `ix_users_email` |
| password_hash | VARCHAR(255) NOT NULL | bcrypt |
| created_at | TIMESTAMPTZ NOT NULL | server default `now()` |

`fdc_foods` — insert-once cache of FDC nutrient data, never updated
| column | type | notes |
| --- | --- | --- |
| fdc_id | INTEGER PK | the FDC identifier, not generated |
| food_name | VARCHAR(500) NOT NULL | |
| energy_kcal_per_100g | NUMERIC(8,2) | nutrient 208 |
| protein_g_per_100g | NUMERIC(8,2) | nutrient 203 |
| fat_g_per_100g | NUMERIC(8,2) | nutrient 204 |
| carbs_g_per_100g | NUMERIC(8,2) | nutrient 205 |
| cached_at | TIMESTAMPTZ NOT NULL | server default `now()` |

`food_log`
| column | type | notes |
| --- | --- | --- |
| id | UUID PK | default `gen_random_uuid()` |
| user_id | UUID NOT NULL | FK -> `users.id` `ON DELETE CASCADE` |
| fdc_id | INTEGER NOT NULL | FK -> `fdc_foods.fdc_id` `ON DELETE RESTRICT` |
| food_name | VARCHAR(500) NOT NULL | snapshot at log time |
| portion_grams | NUMERIC(8,2) NOT NULL | user-entered |
| calories_kcal / protein_g / fat_g / carbs_g | NUMERIC(8,2) NOT NULL | calculated at write time |
| eaten_at | TIMESTAMPTZ NOT NULL | user-provided or server `NOW()` |
| created_at | TIMESTAMPTZ NOT NULL | server default `now()` |

Indexes: `ix_users_email` (unique), `ix_food_log_user_id_eaten_at`
(composite, powers daily + history range queries), `ix_food_log_fdc_id`.

The `pgcrypto` extension is created by the initial migration to guarantee
`gen_random_uuid()` is available for UUID server defaults.

## Migrations

Run automatically on backend container startup:

```sh
sh backend/scripts/run_migrations.sh    # or: cd backend && alembic upgrade head
```

Create a new revision after changing models:

```sh
cd backend && alembic revision --autogenerate -m "describe change"
```

Requires `sqlalchemy>=2.0`, `alembic>=1.13`, `psycopg2-binary` in the backend
image (see `backend/requirements-db.txt`).

## Query helpers (`app.db.queries`)

- `get_user_by_email`, `get_user_by_id`, `create_user`
- `get_cached_food`, `cache_food` (insert-once `ON CONFLICT DO NOTHING`)
- `create_food_log`, `get_food_log`, `delete_food_log` (both scoped to the owner)
- `list_food_logs_for_day`, `daily_totals` — `GET /log/daily`
- `food_logs_grouped_by_day`, `daily_totals_by_day` — `GET /log/history`
- `sum_macros`, `day_bounds` — UTC day helpers

Macros are read from stored columns and never recalculated.
