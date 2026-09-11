import type { MacroTotals } from '../api/types';
import { round0, round1 } from '../lib/format';

interface Props {
  totals: MacroTotals;
  loading?: boolean;
}

/** Four summary cards: calories, protein, fat, carbs. */
export default function MacroCards({ totals, loading = false }: Props) {
  const cards = [
    { key: 'calories', label: 'Calories', value: round0(totals.calories_kcal), unit: 'kcal', tone: 'cal' },
    { key: 'protein', label: 'Protein', value: round1(totals.protein_g), unit: 'g', tone: 'pro' },
    { key: 'fat', label: 'Fat', value: round1(totals.fat_g), unit: 'g', tone: 'fat' },
    { key: 'carbs', label: 'Carbs', value: round1(totals.carbs_g), unit: 'g', tone: 'carb' },
  ];

  return (
    <div className="macro-cards" data-testid="macro-cards">
      {cards.map((card) => (
        <div key={card.key} className={`macro-card macro-card--${card.tone}`}>
          <span className="macro-card__label">{card.label}</span>
          <span className="macro-card__value" data-testid={`total-${card.key}`}>
            {loading ? <span className="skeleton skeleton--value" /> : card.value}
          </span>
          <span className="macro-card__unit">{card.unit}</span>
        </div>
      ))}
    </div>
  );
}
