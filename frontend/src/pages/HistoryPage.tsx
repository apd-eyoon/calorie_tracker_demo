import { useCallback, useEffect, useState, type FormEvent } from 'react';

import { ApiError, api } from '../api/client';
import type { DailyLog } from '../api/types';
import Alert from '../components/Alert';
import EntryList from '../components/EntryList';
import MacroCards from '../components/MacroCards';
import { daysAgoISO, formatDayLabel, todayISO } from '../lib/format';

type Mode = 'day' | 'range';

export default function HistoryPage() {
  const [mode, setMode] = useState<Mode>('day');
  const [day, setDay] = useState(() => daysAgoISO(1));
  const [start, setStart] = useState(() => daysAgoISO(7));
  const [end, setEnd] = useState(() => todayISO());

  const [days, setDays] = useState<DailyLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError('');
      try {
        if (mode === 'day') {
          const result = await api.getDaily(day, signal);
          setDays([result]);
        } else {
          if (start > end) {
            setError('The start date must be on or before the end date.');
            setDays([]);
            return;
          }
          const result = await api.getHistory(start, end, signal);
          setDays(result);
        }
        setLoaded(true);
      } catch (err) {
        if ((err as Error)?.name === 'AbortError') return;
        if (err instanceof ApiError && err.status === 401) return;
        setDays([]);
        setError(err instanceof ApiError ? err.message : 'Could not load history.');
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [mode, day, start, end],
  );

  // Initial load (and reload whenever the selection changes).
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load();
  }

  const daysWithEntries = days.filter((d) => d.entries.length > 0);
  const visibleDays = mode === 'day' ? days : daysWithEntries;
  const maxDate = todayISO();

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">History</h1>
          <p className="page__sub">Review a past day or a range of days.</p>
        </div>
      </div>

      <section className="section card">
        <div className="tabs tabs--inline" role="tablist" aria-label="History mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'day'}
            className={`tab${mode === 'day' ? ' is-active' : ''}`}
            onClick={() => setMode('day')}
          >
            Single day
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'range'}
            className={`tab${mode === 'range' ? ' is-active' : ''}`}
            onClick={() => setMode('range')}
          >
            Date range
          </button>
        </div>

        <form className="form form--inline" onSubmit={handleSubmit}>
          {mode === 'day' ? (
            <label className="field">
              <span className="field__label">Date</span>
              <input
                type="date"
                className="input"
                value={day}
                max={maxDate}
                onChange={(e) => setDay(e.target.value)}
              />
            </label>
          ) : (
            <>
              <label className="field">
                <span className="field__label">Start</span>
                <input
                  type="date"
                  className="input"
                  value={start}
                  max={maxDate}
                  onChange={(e) => setStart(e.target.value)}
                />
              </label>
              <label className="field">
                <span className="field__label">End</span>
                <input
                  type="date"
                  className="input"
                  value={end}
                  max={maxDate}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </label>
            </>
          )}

          <button type="submit" className="btn btn--primary" disabled={loading}>
            {loading ? 'Loading...' : 'View'}
          </button>
        </form>
      </section>

      {error ? <Alert kind="error" message={error} onDismiss={() => setError('')} /> : null}

      {loading ? (
        <section className="section">
          <MacroCards
            totals={{ calories_kcal: 0, protein_g: 0, fat_g: 0, carbs_g: 0 }}
            loading
          />
          <EntryList entries={[]} loading />
        </section>
      ) : visibleDays.length === 0 ? (
        <div className="empty-state">
          <p>
            {loaded
              ? 'No entries logged for the selected period.'
              : 'Pick a date to see your logged foods.'}
          </p>
        </div>
      ) : (
        visibleDays.map((dayLog) => (
          <section className="section day-group" key={dayLog.date || 'unknown'}>
            <div className="section__head">
              <h2 className="section__title">{formatDayLabel(dayLog.date)}</h2>
              <span className="section__count">
                {dayLog.entries.length} item{dayLog.entries.length === 1 ? '' : 's'}
              </span>
            </div>
            <MacroCards totals={dayLog.totals} />
            <EntryList
              entries={dayLog.entries}
              emptyMessage="Nothing was logged on this day."
            />
          </section>
        ))
      )}
    </div>
  );
}
