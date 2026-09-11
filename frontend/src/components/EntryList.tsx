import type { LogEntry } from '../api/types';
import { formatTime, round0, round1 } from '../lib/format';

interface Props {
  entries: LogEntry[];
  loading?: boolean;
  emptyMessage?: string;
  onDelete?: (entry: LogEntry) => void;
  deletingId?: string | null;
}

export default function EntryList({
  entries,
  loading = false,
  emptyMessage = 'No entries yet.',
  onDelete,
  deletingId = null,
}: Props) {
  if (loading) {
    return (
      <ul className="entry-list" aria-busy="true">
        {[0, 1, 2].map((i) => (
          <li key={i} className="entry entry--skeleton">
            <span className="skeleton skeleton--line" />
            <span className="skeleton skeleton--line skeleton--short" />
          </li>
        ))}
      </ul>
    );
  }

  if (!entries.length) {
    return (
      <div className="empty-state" data-testid="empty-entries">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <ul className="entry-list" data-testid="entry-list">
      {entries.map((entry) => (
        <li key={entry.id} className="entry">
          <div className="entry__main">
            <p className="entry__name" title={entry.food_name}>
              {entry.food_name}
            </p>
            <p className="entry__meta">
              {round1(entry.portion_grams)} g &middot; {formatTime(entry.eaten_at)}
            </p>
          </div>

          <div className="entry__macros">
            <span className="pill pill--cal">{round0(entry.calories_kcal)} kcal</span>
            <span className="pill">P {round1(entry.protein_g)}g</span>
            <span className="pill">F {round1(entry.fat_g)}g</span>
            <span className="pill">C {round1(entry.carbs_g)}g</span>
          </div>

          {onDelete ? (
            <button
              type="button"
              className="btn btn--danger btn--icon"
              onClick={() => onDelete(entry)}
              disabled={deletingId === entry.id}
              aria-label={`Delete ${entry.food_name}`}
              title="Delete entry"
            >
              {deletingId === entry.id ? '...' : '\u00d7'}
            </button>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
