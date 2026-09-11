# Calorie Tracker - Frontend (React + TypeScript)

Single-page app built with Vite. The production build is emitted to `dist/` and
copied into the FastAPI image, which serves it from `/` on port **8080** — one
port for both the API and the UI, no nginx.

## Screens

| Route      | Screen           | Notes                                                                |
| ---------- | ---------------- | -------------------------------------------------------------------- |
| `/login`   | Login / Register | Tabbed form, `POST /auth/register` and `POST /auth/login`             |
| `/`        | Dashboard (Today)| `GET /log/daily?date=YYYY-MM-DD`, delete via `DELETE /log/{id}`       |
| `/add`     | Add Food         | Debounced `GET /foods/search?q=`, `GET /foods/{fdcId}`, `POST /log`   |
| `/history` | History          | `GET /log/daily` (single day) and `GET /log/history?start=&end=`      |

## Structure

```
src/
  api/client.ts        shared fetch client: Bearer auth, error normalization, global 401
  api/token.ts         JWT storage in localStorage + change notifications
  api/types.ts         request/response types
  auth/AuthContext.tsx auth state, sign in/out, 401 -> redirect to /login
  auth/RequireAuth.tsx route guard
  components/          AppLayout, MacroCards, EntryList, Alert
  lib/                 date/number formatting, 300 ms debounce hook
  pages/               LoginPage, DashboardPage, AddFoodPage, HistoryPage, NotFoundPage
  styles.css           all styling (no CSS framework dependency)
```

## Behaviour notes

- **Auth:** the JWT returned by `/auth/register` / `/auth/login` is stored under
  `calorie_tracker_jwt` in `localStorage` and attached as
  `Authorization: Bearer <jwt>` to every `/foods/*` and `/log/*` request.
- **401 handling:** any 401 clears the token and redirects to `/login` with an
  "session expired" notice.
- **Debounce:** the food search waits 300 ms after the last keystroke, aborts
  in-flight requests, and requires at least 2 characters.
- **Live preview:** macros are recomputed on every keystroke as
  `(per_100g / 100) * portion_grams`.
- **`eaten_at`:** a blank `datetime-local` field is omitted from the payload so
  the server defaults to UTC now; future values are blocked client-side.
- **FDC API key:** never referenced or stored in the frontend — all FDC traffic
  goes through the backend proxy endpoints.

## Local development

```bash
npm install
npm run dev     # http://localhost:5173, proxies /auth, /foods, /log to :8080
npm run build   # emits dist/
```

Set `VITE_API_BASE_URL` only if the API lives on a different origin; by default
all requests are same-origin.
