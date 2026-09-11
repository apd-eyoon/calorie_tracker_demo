/** Client-side JWT storage (localStorage) + change notifications. */

const TOKEN_KEY = 'calorie_tracker_jwt';

type Listener = (token: string | null) => void;

const listeners = new Set<Listener>();

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable (private mode) - keep going in-memory only */
  }
  listeners.forEach((fn) => fn(token));
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
  listeners.forEach((fn) => fn(null));
}

export function onTokenChange(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
