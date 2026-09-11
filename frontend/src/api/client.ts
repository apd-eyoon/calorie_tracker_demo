/**
 * Shared API client.
 *
 * - Attaches `Authorization: Bearer <jwt>` to every authenticated request.
 * - Normalizes FastAPI error payloads (string `detail`, list of validation
 *   errors, or `{message}`) into a single readable message.
 * - Globally handles 401 by clearing the token and notifying the app so the
 *   router can redirect to the login screen.
 *
 * The FDC API key is never referenced here - all FDC traffic goes through the
 * backend proxy endpoints.
 */

import { clearToken, getToken } from './token';
import type {
  AuthResponse,
  CreateLogPayload,
  DailyLog,
  FoodDetail,
  FoodSearchResult,
  LogEntry,
  MacroTotals,
} from './types';
import { emptyTotals } from './types';

/** Same-origin by default: FastAPI serves the built SPA from `/`. */
export const API_BASE_URL = (
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? ''
).replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

/** Register the app-level reaction to a 401 (redirect to /login). */
export function setUnauthorizedHandler(fn: UnauthorizedHandler | null): void {
  unauthorizedHandler = fn;
}

function extractMessage(payload: unknown, status: number): string {
  if (typeof payload === 'string' && payload.trim()) return payload.trim();

  if (payload && typeof payload === 'object') {
    const body = payload as Record<string, unknown>;
    const detail = body.detail ?? body.message ?? body.error;

    if (typeof detail === 'string' && detail.trim()) return detail.trim();

    // FastAPI 422: detail is a list of {loc, msg, type}
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const entry = item as Record<string, unknown>;
            const loc = Array.isArray(entry.loc)
              ? entry.loc.filter((p) => p !== 'body').join('.')
              : '';
            const msg = typeof entry.msg === 'string' ? entry.msg : '';
            return loc ? `${loc}: ${msg}` : msg;
          }
          return '';
        })
        .filter(Boolean);
      if (parts.length) return parts.join('; ');
    }
  }

  if (status === 401) return 'Your session has expired. Please log in again.';
  if (status === 403) return 'You are not allowed to perform that action.';
  if (status === 404) return 'Not found.';
  if (status >= 500) return 'The server ran into a problem. Please try again.';
  return `Request failed (HTTP ${status}).`;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** Attach the bearer token (default: true). */
  auth?: boolean;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = options;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error)?.name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the server. Check your connection.', 0);
  }

  if (response.status === 204) return undefined as T;

  const raw = await response.text();
  let payload: unknown = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      clearToken();
      if (unauthorizedHandler) unauthorizedHandler();
    }
    throw new ApiError(extractMessage(payload, response.status), response.status, payload);
  }

  return payload as T;
}

// --------------------------------------------------------------------------
// normalizers - tolerate minor shape differences from the backend
// --------------------------------------------------------------------------
const num = (value: unknown): number => {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

function normalizeEntry(raw: any): LogEntry {
  return {
    id: String(raw?.id ?? ''),
    fdc_id: num(raw?.fdc_id ?? raw?.fdcId),
    food_name: String(raw?.food_name ?? raw?.foodName ?? raw?.name ?? 'Unknown food'),
    portion_grams: num(raw?.portion_grams ?? raw?.portionGrams),
    calories_kcal: num(raw?.calories_kcal ?? raw?.caloriesKcal ?? raw?.calories),
    protein_g: num(raw?.protein_g ?? raw?.proteinG ?? raw?.protein),
    fat_g: num(raw?.fat_g ?? raw?.fatG ?? raw?.fat),
    carbs_g: num(raw?.carbs_g ?? raw?.carbsG ?? raw?.carbs),
    eaten_at: String(raw?.eaten_at ?? raw?.eatenAt ?? ''),
    created_at: raw?.created_at ?? raw?.createdAt,
  };
}

function normalizeTotals(raw: any): MacroTotals {
  if (!raw || typeof raw !== 'object') return emptyTotals();
  return {
    calories_kcal: num(raw.calories_kcal ?? raw.caloriesKcal ?? raw.calories ?? raw.total_calories_kcal),
    protein_g: num(raw.protein_g ?? raw.proteinG ?? raw.protein ?? raw.total_protein_g),
    fat_g: num(raw.fat_g ?? raw.fatG ?? raw.fat ?? raw.total_fat_g),
    carbs_g: num(raw.carbs_g ?? raw.carbsG ?? raw.carbs ?? raw.total_carbs_g),
  };
}

function sumEntries(entries: LogEntry[]): MacroTotals {
  return entries.reduce<MacroTotals>(
    (acc, entry) => ({
      calories_kcal: acc.calories_kcal + entry.calories_kcal,
      protein_g: acc.protein_g + entry.protein_g,
      fat_g: acc.fat_g + entry.fat_g,
      carbs_g: acc.carbs_g + entry.carbs_g,
    }),
    emptyTotals(),
  );
}

function normalizeDaily(raw: any, fallbackDate: string): DailyLog {
  const entriesRaw = Array.isArray(raw)
    ? raw
    : raw?.entries ?? raw?.items ?? raw?.logs ?? [];
  const entries = (Array.isArray(entriesRaw) ? entriesRaw : []).map(normalizeEntry);
  const totalsRaw = Array.isArray(raw) ? null : raw?.totals ?? raw?.total ?? raw?.macros ?? raw;
  const totals = totalsRaw ? normalizeTotals(totalsRaw) : sumEntries(entries);
  const hasTotals =
    totals.calories_kcal || totals.protein_g || totals.fat_g || totals.carbs_g;

  return {
    date: String((Array.isArray(raw) ? null : raw?.date) ?? fallbackDate),
    totals: hasTotals ? totals : sumEntries(entries),
    entries,
  };
}

// --------------------------------------------------------------------------
// endpoints
// --------------------------------------------------------------------------
export const api = {
  register(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
  },

  login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
  },

  async searchFoods(query: string, signal?: AbortSignal): Promise<FoodSearchResult[]> {
    const raw = await request<any>(`/foods/search?q=${encodeURIComponent(query)}`, { signal });
    const list = Array.isArray(raw) ? raw : raw?.results ?? raw?.foods ?? raw?.items ?? [];
    return (Array.isArray(list) ? list : []).map((item: any) => ({
      fdcId: num(item?.fdcId ?? item?.fdc_id),
      name: String(item?.name ?? item?.description ?? item?.food_name ?? 'Unnamed food'),
      brandOwner: item?.brandOwner ?? item?.brand_owner ?? item?.brandName ?? null,
    }));
  },

  async getFood(fdcId: number, signal?: AbortSignal): Promise<FoodDetail> {
    const raw = await request<any>(`/foods/${fdcId}`, { signal });
    return {
      fdcId: num(raw?.fdcId ?? raw?.fdc_id ?? fdcId),
      name: String(raw?.name ?? raw?.food_name ?? raw?.description ?? 'Unnamed food'),
      brandOwner: raw?.brandOwner ?? raw?.brand_owner ?? null,
      energy_kcal_per_100g: num(
        raw?.energy_kcal_per_100g ?? raw?.energyKcalPer100g ?? raw?.calories_kcal_per_100g,
      ),
      protein_g_per_100g: num(raw?.protein_g_per_100g ?? raw?.proteinGPer100g),
      fat_g_per_100g: num(raw?.fat_g_per_100g ?? raw?.fatGPer100g),
      carbs_g_per_100g: num(raw?.carbs_g_per_100g ?? raw?.carbsGPer100g),
    };
  },

  async createLog(payload: CreateLogPayload): Promise<LogEntry> {
    const raw = await request<any>('/log', { method: 'POST', body: payload });
    return normalizeEntry(raw ?? {});
  },

  async getDaily(date: string, signal?: AbortSignal): Promise<DailyLog> {
    const raw = await request<any>(`/log/daily?date=${encodeURIComponent(date)}`, { signal });
    return normalizeDaily(raw, date);
  },

  async getHistory(start: string, end: string, signal?: AbortSignal): Promise<DailyLog[]> {
    const raw = await request<any>(
      `/log/history?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      { signal },
    );
    const source = Array.isArray(raw)
      ? raw
      : raw?.days ?? raw?.history ?? raw?.results ?? raw?.entries ?? [];
    const list: any[] = Array.isArray(source) ? source : [];

    // The backend may return either day groups ({date, totals, entries}) or a
    // flat list of entries - group flat entries by local calendar day.
    const looksGrouped = list.some(
      (item) => item && typeof item === 'object' && ('entries' in item || 'items' in item),
    );

    if (looksGrouped) {
      return list
        .map((day: any) => normalizeDaily(day, String(day?.date ?? '')))
        .sort((a, b) => (a.date < b.date ? 1 : -1));
    }

    const buckets = new Map<string, LogEntry[]>();
    list.map(normalizeEntry).forEach((entry) => {
      const key = entry.eaten_at ? entry.eaten_at.slice(0, 10) : start;
      const bucket = buckets.get(key);
      if (bucket) bucket.push(entry);
      else buckets.set(key, [entry]);
    });

    return Array.from(buckets.entries())
      .sort((a, b) => (a[0] < b[0] ? 1 : -1))
      .map(([date, entries]) => ({ date, totals: sumEntries(entries), entries }));
  },

  deleteLog(id: string): Promise<void> {
    return request<void>(`/log/${encodeURIComponent(id)}`, { method: 'DELETE' });
  },
};

export { sumEntries };
