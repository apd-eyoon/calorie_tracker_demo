/** Shared API types for the calorie tracker frontend. */

export interface AuthResponse {
  access_token: string;
  token_type?: string;
}

export interface FoodSearchResult {
  fdcId: number;
  name: string;
  brandOwner?: string | null;
}

/** Macros per 100 g, as returned by GET /foods/{fdcId}. */
export interface FoodDetail {
  fdcId: number;
  name: string;
  brandOwner?: string | null;
  energy_kcal_per_100g: number;
  protein_g_per_100g: number;
  fat_g_per_100g: number;
  carbs_g_per_100g: number;
}

export interface LogEntry {
  id: string;
  fdc_id: number;
  food_name: string;
  portion_grams: number;
  calories_kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  eaten_at: string;
  created_at?: string;
}

export interface MacroTotals {
  calories_kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
}

export interface DailyLog {
  date: string;
  totals: MacroTotals;
  entries: LogEntry[];
}

export interface CreateLogPayload {
  fdc_id: number;
  portion_grams: number;
  /** ISO-8601 string; omitted entirely when the user leaves the field blank. */
  eaten_at?: string;
}

export const emptyTotals = (): MacroTotals => ({
  calories_kcal: 0,
  protein_g: 0,
  fat_g: 0,
  carbs_g: 0,
});
