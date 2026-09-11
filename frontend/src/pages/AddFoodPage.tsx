import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { ApiError, api } from '../api/client';
import type { FoodDetail, FoodSearchResult } from '../api/types';
import Alert from '../components/Alert';
import { localInputToISO, nowLocalInputValue, round0, round1 } from '../lib/format';
import { useDebouncedValue } from '../lib/useDebouncedValue';

export default function AddFoodPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [query, setQuery] = useState(() => searchParams.get('q') ?? '');
  const debouncedQuery = useDebouncedValue(query, 300);

  const [results, setResults] = useState<FoodSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searched, setSearched] = useState(false);

  const [selected, setSelected] = useState<FoodDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [portion, setPortion] = useState('100');
  const [eatenAt, setEatenAt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const searchBoxRef = useRef<HTMLDivElement | null>(null);

  // ---- debounced search -------------------------------------------------
  useEffect(() => {
    const term = debouncedQuery.trim();
    if (term.length < 2) {
      setResults([]);
      setSearching(false);
      setSearchError('');
      setSearched(false);
      return;
    }

    const controller = new AbortController();
    setSearching(true);
    setSearchError('');

    api
      .searchFoods(term, controller.signal)
      .then((items) => {
        setResults(items);
        setSearched(true);
        setDropdownOpen(true);
      })
      .catch((err) => {
        if ((err as Error)?.name === 'AbortError') return;
        if (err instanceof ApiError && err.status === 401) return;
        setResults([]);
        setSearchError(err instanceof ApiError ? err.message : 'Food search failed.');
        setDropdownOpen(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setSearching(false);
      });

    return () => controller.abort();
  }, [debouncedQuery]);

  // Close the dropdown when clicking outside the search box.
  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (searchBoxRef.current && !searchBoxRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  async function handlePick(item: FoodSearchResult) {
    setDropdownOpen(false);
    setFormError('');
    setLoadingDetail(true);
    setSelected(null);
    try {
      const detail = await api.getFood(item.fdcId);
      setSelected({
        ...detail,
        name: detail.name || item.name,
        brandOwner: detail.brandOwner ?? item.brandOwner ?? null,
      });
      setPortion((prev) => prev || '100');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setFormError(
        err instanceof ApiError ? err.message : 'Could not load nutrition details for that food.',
      );
    } finally {
      setLoadingDetail(false);
    }
  }

  // ---- live macro preview: (per_100g / 100) * portion_grams --------------
  const portionGrams = Number.parseFloat(portion);
  const validPortion = Number.isFinite(portionGrams) && portionGrams > 0;

  const preview = useMemo(() => {
    const factor = validPortion ? portionGrams / 100 : 0;
    return {
      calories: (selected?.energy_kcal_per_100g ?? 0) * factor,
      protein: (selected?.protein_g_per_100g ?? 0) * factor,
      fat: (selected?.fat_g_per_100g ?? 0) * factor,
      carbs: (selected?.carbs_g_per_100g ?? 0) * factor,
    };
  }, [selected, portionGrams, validPortion]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;

    if (!validPortion) {
      setFormError('Enter a portion size in grams greater than 0.');
      return;
    }

    const isoEatenAt = eatenAt ? localInputToISO(eatenAt) : undefined;
    if (eatenAt && !isoEatenAt) {
      setFormError('That date/time is not valid.');
      return;
    }
    if (isoEatenAt && new Date(isoEatenAt).getTime() > Date.now()) {
      setFormError('The "eaten at" time cannot be in the future.');
      return;
    }

    setSubmitting(true);
    setFormError('');
    try {
      await api.createLog({
        fdc_id: selected.fdcId,
        portion_grams: portionGrams,
        ...(isoEatenAt ? { eaten_at: isoEatenAt } : {}),
      });
      navigate('/', { replace: true, state: { notice: `Logged ${selected.name}.` } });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setFormError(err instanceof ApiError ? err.message : 'Could not save that entry.');
    } finally {
      setSubmitting(false);
    }
  }

  function resetSelection() {
    setSelected(null);
    setFormError('');
    setEatenAt('');
  }

  const showDropdown =
    dropdownOpen && (searching || Boolean(searchError) || results.length > 0 || searched);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Add Food</h1>
          <p className="page__sub">Search the USDA food database, then log a portion.</p>
        </div>
        <button type="button" className="btn btn--ghost" onClick={() => navigate('/')}>
          Back to Today
        </button>
      </div>

      <section className="section">
        <div className="search-box" ref={searchBoxRef}>
          <input
            type="search"
            className="input input--lg"
            placeholder="Search foods (e.g. greek yogurt)"
            aria-label="Search foods"
            autoComplete="off"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setDropdownOpen(true);
            }}
            onFocus={() => setDropdownOpen(true)}
          />
          {searching ? <span className="search-box__spinner" aria-label="Searching" /> : null}

          {showDropdown ? (
            <ul className="dropdown" role="listbox" aria-label="Food search results">
              {searching ? (
                <li className="dropdown__status">Searching...</li>
              ) : searchError ? (
                <li className="dropdown__status dropdown__status--error">{searchError}</li>
              ) : results.length === 0 ? (
                <li className="dropdown__status">
                  {debouncedQuery.trim().length < 2
                    ? 'Type at least 2 characters to search.'
                    : `No foods found for "${debouncedQuery.trim()}".`}
                </li>
              ) : (
                results.map((item) => (
                  <li key={item.fdcId}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selected?.fdcId === item.fdcId}
                      className="dropdown__item"
                      onClick={() => handlePick(item)}
                    >
                      <span className="dropdown__name">{item.name}</span>
                      {item.brandOwner ? (
                        <span className="dropdown__brand">{item.brandOwner}</span>
                      ) : null}
                    </button>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </div>
      </section>

      {formError ? <Alert kind="error" message={formError} onDismiss={() => setFormError('')} /> : null}

      {loadingDetail ? (
        <section className="section card">
          <p className="muted">Loading nutrition details...</p>
        </section>
      ) : null}

      {selected && !loadingDetail ? (
        <section className="section card" aria-label="Log portion">
          <form className="form" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field__label">Food</span>
              <input className="input" value={selected.name} readOnly aria-readonly="true" />
            </label>
            {selected.brandOwner ? <p className="muted">Brand: {selected.brandOwner}</p> : null}

            <div className="field-row">
              <label className="field">
                <span className="field__label">
                  Portion (grams) <span className="req">*</span>
                </span>
                <input
                  type="number"
                  className="input"
                  min="0.1"
                  step="0.1"
                  required
                  value={portion}
                  onChange={(e) => setPortion(e.target.value)}
                  placeholder="100"
                />
              </label>

              <label className="field">
                <span className="field__label">Eaten at (optional)</span>
                <input
                  type="datetime-local"
                  className="input"
                  value={eatenAt}
                  max={nowLocalInputValue()}
                  onChange={(e) => setEatenAt(e.target.value)}
                />
                <span className="field__hint">Leave blank to use the current server time.</span>
              </label>
            </div>

            <div className="preview" aria-live="polite">
              <h3 className="preview__title">
                Macro preview{validPortion ? ` for ${round1(portionGrams)} g` : ''}
              </h3>
              <div className="preview__grid">
                <div className="preview__item">
                  <span className="preview__label">Calories</span>
                  <span className="preview__value">{round0(preview.calories)}</span>
                  <span className="preview__unit">kcal</span>
                </div>
                <div className="preview__item">
                  <span className="preview__label">Protein</span>
                  <span className="preview__value">{round1(preview.protein)}</span>
                  <span className="preview__unit">g</span>
                </div>
                <div className="preview__item">
                  <span className="preview__label">Fat</span>
                  <span className="preview__value">{round1(preview.fat)}</span>
                  <span className="preview__unit">g</span>
                </div>
                <div className="preview__item">
                  <span className="preview__label">Carbs</span>
                  <span className="preview__value">{round1(preview.carbs)}</span>
                  <span className="preview__unit">g</span>
                </div>
              </div>
              <p className="muted preview__per100">
                Per 100 g: {round0(selected.energy_kcal_per_100g)} kcal &middot; P{' '}
                {round1(selected.protein_g_per_100g)} g &middot; F {round1(selected.fat_g_per_100g)} g
                &middot; C {round1(selected.carbs_g_per_100g)} g
              </p>
            </div>

            <div className="form__actions">
              <button type="submit" className="btn btn--primary" disabled={submitting || !validPortion}>
                {submitting ? 'Saving...' : 'Log this food'}
              </button>
              <button type="button" className="btn btn--ghost" onClick={resetSelection}>
                Cancel
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {!selected && !loadingDetail ? (
        <div className="empty-state">
          <p>Start typing above to find a food, then pick a result to log a portion.</p>
        </div>
      ) : null}
    </div>
  );
}
