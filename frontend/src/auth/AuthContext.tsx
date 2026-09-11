import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';

import { setUnauthorizedHandler } from '../api/client';
import { clearToken, getToken, onTokenChange, setToken } from '../api/token';

interface AuthContextValue {
  token: string | null;
  email: string | null;
  isAuthenticated: boolean;
  signIn: (token: string, email?: string) => void;
  signOut: () => void;
}

const EMAIL_KEY = 'calorie_tracker_email';

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Best-effort decode of the `sub`/`email` claim for display purposes only. */
function emailFromToken(token: string | null): string | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const json = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const claims = JSON.parse(json) as Record<string, unknown>;
    const value = claims.email ?? claims.sub;
    return typeof value === 'string' && value.includes('@') ? value : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [email, setEmail] = useState<string | null>(() => {
    try {
      return window.localStorage.getItem(EMAIL_KEY) || emailFromToken(getToken());
    } catch {
      return null;
    }
  });

  // Keep state in sync when the token is cleared from the API layer (401) or
  // from another browser tab.
  useEffect(() => {
    const unsubscribe = onTokenChange((next) => setTokenState(next));
    const onStorage = () => setTokenState(getToken());
    window.addEventListener('storage', onStorage);
    return () => {
      unsubscribe();
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const signIn = useCallback((nextToken: string, nextEmail?: string) => {
    setToken(nextToken);
    setTokenState(nextToken);
    const resolved = nextEmail || emailFromToken(nextToken);
    setEmail(resolved);
    try {
      if (resolved) window.localStorage.setItem(EMAIL_KEY, resolved);
    } catch {
      /* ignore */
    }
  }, []);

  const signOut = useCallback(() => {
    clearToken();
    setTokenState(null);
    setEmail(null);
    try {
      window.localStorage.removeItem(EMAIL_KEY);
    } catch {
      /* ignore */
    }
    navigate('/login', { replace: true });
  }, [navigate]);

  // Global 401 handling: token already cleared by the client, just redirect.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setTokenState(null);
      navigate('/login', { replace: true, state: { expired: true } });
    });
    return () => setUnauthorizedHandler(null);
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({ token, email, isAuthenticated: Boolean(token), signIn, signOut }),
    [token, email, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside an <AuthProvider>');
  return ctx;
}
