export interface User {
  id: number
  email: string
  username: string
}

export interface Tokens {
  access: string
  refresh: string
}

export type CategoriaIngrediente =
  | 'verdura'
  | 'fruta'
  | 'carne'
  | 'pescado'
  | 'lacteo'
  | 'cereal'
  | 'legumbre'
  | 'especia'
  | 'bebida'
  | 'otro'
  | ''

export interface Ingredient {
  id: number
  name: string
  normalized_name: string
  category: CategoriaIngrediente
  quantity: string
  in_pantry: boolean
  created_at: string
}

export interface ShoppingItem {
  id: number
  name: string
  normalized_name: string
  quantity: string
  category: CategoriaIngrediente
  bought: boolean
  created_at: string
}

export interface RecipeIngredient {
  ingredient: string
  measure: string
}

export interface MissingIngredient extends RecipeIngredient {
  name_es: string | null
}

export interface RecipeMatch {
  match_score: number
  matched_ingredients: string[]
  missing_ingredients: string[]
  missing: MissingIngredient[]
}

export interface Recipe {
  external_id: string
  title: string
  image: string
  category: string
  area: string
  instructions: string
  ingredients: RecipeIngredient[]
  source: string
  match?: RecipeMatch
  /** Título en inglés, cuando la receta viene traducida. */
  original_title?: string
  meal_type?: string
  /** Solo en las recetas de la IA guardadas (source === 'ai'). */
  description?: string
  estimated_minutes?: number | null
  difficulty?: string
  servings?: number | null
  image_credit?: string
  image_page?: string
  steps?: AiStep[]
  tips?: string[]
  prep_minutes?: number | null
  cook_minutes?: number | null
  /** Cómo se tradujo al español. `complete: false` = alguna parte se quedó en inglés. */
  translation?: { lang: string; provider: string | null; complete: boolean }
}

export interface RecipeSummary {
  external_id: string
  title: string
  image: string
  category: string
  area: string
  match_score: number
  matched_ingredients: string[]
  missing_ingredients: string[]
  source: string
  original_title?: string
  meal_type?: string
}

export interface SuggestionsResponse {
  count: number
  results: RecipeSummary[]
}

export interface SuggestionFilters {
  category: string
  maxMissing: number | null
  search: string
}

export interface Favorite {
  id: number
  recipe: Recipe
  notes: string
  created_at: string
}

/** Un paso de una receta de la IA, con el tiempo de espera si lo tiene (cocción, horno, reposo). */
export interface AiStep {
  text: string
  minutes: number | null
}

export interface AiSuggestion {
  title: string
  description: string
  meal_type: string
  servings: number | null
  ingredients: { name: string; quantity: string }[]
  ingredients_used: string[]
  missing_ingredients: string[]
  steps: AiStep[]
  tips: string[]
  estimated_minutes: number | null
  prep_minutes: number | null
  cook_minutes: number | null
  difficulty: string
  photo_query?: string
  photo_query_en?: string
  /** Foto orientativa de Wikipedia; null si no hay un artículo fiable sobre el plato. */
  image: { url: string; credit: string; page: string } | null
  /** El servidor la guarda sola en el recetario del usuario; este es su identificador. */
  external_id?: string | null
  saved?: boolean
}

export interface AiAdaptation {
  substitutions: { original: string; substitute: string; note: string }[]
  adapted_steps: string[]
  warnings: string[]
}

// --- Dieta semanal ---

export type TipoComidaPlan = 'desayuno' | 'almuerzo' | 'merienda' | 'cena' | 'snack'

export interface ComidaPlan {
  type: TipoComidaPlan
  title: string
  description: string
  calories: number | null
  ingredients: string[]
}

export interface DiaPlan {
  day: string
  meals: ComidaPlan[]
}

export interface OpcionesPlan {
  goal: string
  meals: string[]
  calories: number | null
  diet: string
  avoid: string[]
  use_pantry: boolean
}

// --- Catálogo de platos ---

export interface Plato {
  id: number
  name_es: string
  name_en: string
  description: string
  country: string
  meal_type: string
  diets: string[]
  ingredients: { ingredient: string; measure: string }[]
  steps: string
  calories: number | null
  image: string
  image_credit: string
  image_license: string
  reviewed: boolean
  source: string
}

export interface FiltrosPlatos {
  country?: string
  meal?: string
  diet?: string
  q?: string
  limit?: number
  offset?: number
}

export interface MealPlan {
  id: number
  title: string
  options: OpcionesPlan
  days: DiaPlan[]
  notes: string
  created_at: string
}
