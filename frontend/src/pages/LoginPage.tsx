import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError, api } from '../api/client';
import Alert from '../components/Alert';
import { useAuth } from '../auth/AuthContext';

type Tab = 'login' | 'register';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, signIn } = useAuth();

  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = (location.state as { from?: string } | null)?.from || '/';
  const sessionExpired = Boolean((location.state as { expired?: boolean } | null)?.expired);

  useEffect(() => {
    if (isAuthenticated) navigate(redirectTo, { replace: true });
  }, [isAuthenticated, navigate, redirectTo]);

  useEffect(() => {
    if (sessionExpired) setNotice('Your session expired. Please log in again.');
  }, [sessionExpired]);

  function switchTab(next: Tab) {
    setTab(next);
    setError('');
    setNotice('');
    setConfirm('');
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setNotice('');

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError('Email and password are required.');
      return;
    }
    if (tab === 'register') {
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
      if (password !== confirm) {
        setError('Passwords do not match.');
        return;
      }
    }

    setSubmitting(true);
    try {
      const result =
        tab === 'register'
          ? await api.register(trimmedEmail, password)
          : await api.login(trimmedEmail, password);

      const token = result?.access_token;
      if (!token) {
        setError('The server did not return a token. Please try again.');
        return;
      }
      signIn(token, trimmedEmail);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Something went wrong. Please try again.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__head">
          <span className="brand__mark brand__mark--lg" aria-hidden="true">
            &#9679;
          </span>
          <h1>Calorie Tracker</h1>
          <p className="auth-card__sub">Search foods, log portions, track your macros.</p>
        </div>

        <div className="tabs" role="tablist" aria-label="Authentication">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'login'}
            className={`tab${tab === 'login' ? ' is-active' : ''}`}
            onClick={() => switchTab('login')}
          >
            Log in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'register'}
            className={`tab${tab === 'register' ? ' is-active' : ''}`}
            onClick={() => switchTab('register')}
          >
            Register
          </button>
        </div>

        {notice ? <Alert kind="info" message={notice} onDismiss={() => setNotice('')} /> : null}
        {error ? <Alert kind="error" message={error} /> : null}

        <form className="form" onSubmit={handleSubmit} noValidate>
          <label className="field">
            <span className="field__label">Email</span>
            <input
              type="email"
              name="email"
              autoComplete="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="field">
            <span className="field__label">Password</span>
            <input
              type="password"
              name="password"
              autoComplete={tab === 'register' ? 'new-password' : 'current-password'}
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={tab === 'register' ? 'At least 8 characters' : 'Your password'}
              required
            />
          </label>

          {tab === 'register' ? (
            <label className="field">
              <span className="field__label">Confirm password</span>
              <input
                type="password"
                name="confirm"
                autoComplete="new-password"
                className="input"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat your password"
                required
              />
            </label>
          ) : null}

          <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
            {submitting
              ? tab === 'register'
                ? 'Creating account...'
                : 'Logging in...'
              : tab === 'register'
                ? 'Create account'
                : 'Log in'}
          </button>
        </form>

        <p className="auth-card__foot">
          {tab === 'login' ? (
            <>
              No account yet?{' '}
              <button type="button" className="linkish" onClick={() => switchTab('register')}>
                Register
              </button>
            </>
          ) : (
            <>
              Already registered?{' '}
              <button type="button" className="linkish" onClick={() => switchTab('login')}>
                Log in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
