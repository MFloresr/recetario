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

export interface AiSuggestion {
  title: string
  description: string
  ingredients_used: string[]
  missing_ingredients: string[]
  steps: string[]
  estimated_minutes: number | null
  difficulty: string
}

export interface AiAdaptation {
  substitutions: { original: string; substitute: string; note: string }[]
  adapted_steps: string[]
  warnings: string[]
}
