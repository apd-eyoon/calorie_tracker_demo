import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError, api } from '../api/client';
import type { DailyLog, LogEntry } from '../api/types';
import { emptyTotals } from '../api/types';
import Alert from '../components/Alert';
import EntryList from '../components/EntryList';
import MacroCards from '../components/MacroCards';
import { formatDayLabel, todayISO } from '../lib/format';

export default function DashboardPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [date] = useState(() => todayISO());
  const [daily, setDaily] = useState<DailyLog>({ date, totals: emptyTotals(), entries: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(
    (location.state as { notice?: string } | null)?.notice ?? '',
  );
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [quickQuery, setQuickQuery] = useState('');

  // Clear one-shot navigation state so the banner doesn't reappear on refresh.
  useEffect(() => {
    if ((location.state as { notice?: string } | null)?.notice) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError('');
      try {
        const result = await api.getDaily(date, signal);
        setDaily(result);
      } catch (err) {
        if ((err as Error)?.name === 'AbortError') return;
        if (err instanceof ApiError && err.status === 401) return; // handled globally
        setError(err instanceof ApiError ? err.message : "Could not load today's log.");
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [date],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function handleDelete(entry: LogEntry) {
    if (!window.confirm(`Delete "${entry.food_name}" from today's log?`)) return;
    setDeletingId(entry.id);
    setError('');
    try {
      await api.deleteLog(entry.id);
      setNotice('Entry deleted.');
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setError(err instanceof ApiError ? err.message : 'Could not delete that entry.');
    } finally {
      setDeletingId(null);
    }
  }

  function handleQuickSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = quickQuery.trim();
    navigate(q ? `/add?q=${encodeURIComponent(q)}` : '/add');
  }

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Today</h1>
          <p className="page__sub">{formatDayLabel(date)}</p>
        </div>

        <form className="search-bar" onSubmit={handleQuickSearch} role="search">
          <input
            type="search"
            className="input"
            placeholder="Search foods (e.g. banana)"
            aria-label="Search foods"
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
          />
          <button type="submit" className="btn btn--primary">
            + Add Food
          </button>
        </form>
      </div>

      {notice ? <Alert kind="success" message={notice} onDismiss={() => setNotice('')} /> : null}
      {error ? <Alert kind="error" message={error} onDismiss={() => setError('')} /> : null}

      <section className="section" aria-label="Daily totals">
        <MacroCards totals={daily.totals} loading={loading} />
      </section>

      <section className="section" aria-label="Today's entries">
        <div className="section__head">
          <h2 className="section__title">Entries</h2>
          <span className="section__count">
            {loading ? '' : `${daily.entries.length} item${daily.entries.length === 1 ? '' : 's'}`}
          </span>
        </div>

        <EntryList
          entries={daily.entries}
          loading={loading}
          emptyMessage="Nothing logged yet today. Use the search bar above to add your first food."
          onDelete={handleDelete}
          deletingId={deletingId}
        />
      </section>
    </div>
  );
}
