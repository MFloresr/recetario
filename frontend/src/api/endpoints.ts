import { api } from './client'
import type {
  AiAdaptation,
  AiSuggestion,
  Favorite,
  FiltrosPlatos,
  Ingredient,
  MealPlan,
  OpcionesPlan,
  Plato,
  Recipe,
  ShoppingItem,
  SuggestionFilters,
  SuggestionsResponse,
  Tokens,
  User,
} from '@/types/api'

/** La app se muestra en español: el backend traduce las recetas de TheMealDB (que está en inglés). */
const IDIOMA = 'es'

/** La IA puede tardar bastante más que el resto de la API (y probar modelos de reserva). */
const TIEMPO_IA = 100_000

export interface EstadoApi {
  status: string
}

export async function comprobarApi(): Promise<EstadoApi> {
  const { data } = await api.get<EstadoApi>('/health/', { _sinCarga: true })
  return data
}

// --- Autenticación ---

export interface DatosRegistro {
  email: string
  username: string
  password: string
}

export const authApi = {
  register: async (datos: DatosRegistro) => (await api.post<User>('/auth/register/', datos)).data,
  login: async (identificador: string, password: string) => {
    const cuerpo = identificador.includes('@')
      ? { email: identificador, password }
      : { username: identificador, password }
    return (await api.post<Tokens>('/auth/login/', cuerpo)).data
  },
  me: async () => (await api.get<User>('/auth/me/')).data,
  /** Borra la cuenta y todos sus datos; exige la contraseña. */
  deleteAccount: async (password: string) => {
    await api.delete('/auth/me/', { data: { password } })
  },
}

// --- Despensa ---

export const ingredientsApi = {
  list: async () => (await api.get<Ingredient[]>('/ingredients/')).data,
  create: async (name: string, quantity = '') =>
    (await api.post<Ingredient>('/ingredients/', { name, quantity })).data,
  update: async (
    id: number,
    cambios: Partial<Pick<Ingredient, 'name' | 'quantity' | 'category' | 'in_pantry'>>,
  ) => (await api.patch<Ingredient>(`/ingredients/${id}/`, cambios)).data,
  remove: async (id: number) => {
    await api.delete(`/ingredients/${id}/`)
  },
}

// --- Lista de la compra ---

export const shoppingApi = {
  list: async () => (await api.get<ShoppingItem[]>('/shopping-list/')).data,
  create: async (name: string, quantity = '') =>
    (await api.post<ShoppingItem>('/shopping-list/', { name, quantity })).data,
  update: async (
    id: number,
    cambios: Partial<Pick<ShoppingItem, 'bought' | 'quantity' | 'name'>>,
  ) => (await api.patch<ShoppingItem>(`/shopping-list/${id}/`, cambios)).data,
  remove: async (id: number) => {
    await api.delete(`/shopping-list/${id}/`)
  },
  clearBought: async () =>
    (await api.post<{ deleted: number }>('/shopping-list/clear-bought/')).data,
}

// --- Recetas y favoritos ---

export const recipesApi = {
  suggestions: async (ingredientes: string[], filtros: SuggestionFilters) => {
    const params: Record<string, string | number> = {
      ingredients: ingredientes.join(','),
      lang: IDIOMA,
    }
    if (filtros.category) params.category = filtros.category
    if (filtros.maxMissing !== null) params.max_missing = filtros.maxMissing
    if (filtros.search.trim()) params.search = filtros.search.trim()
    return (await api.get<SuggestionsResponse>('/recipes/suggestions/', { params })).data
  },
  detail: async (externalId: string, ingredientes: string[] = []) =>
    (
      await api.get<Recipe>(`/recipes/${encodeURIComponent(externalId)}/`, {
        params: {
          lang: IDIOMA,
          ...(ingredientes.length ? { ingredients: ingredientes.join(',') } : {}),
        },
      })
    ).data,
}

export const favoritesApi = {
  list: async () => (await api.get<Favorite[]>('/favorites/', { params: { lang: IDIOMA } })).data,
  create: async (externalId: string) =>
    (
      await api.post<Favorite>(
        '/favorites/',
        { external_id: externalId },
        { params: { lang: IDIOMA } },
      )
    ).data,
  /** Guarda en el recetario una receta propuesta por la IA. */
  createFromAi: async (s: AiSuggestion) =>
    (
      await api.post<Favorite>(
        '/favorites/',
        {
          recipe: {
            title: s.title,
            description: s.description,
            meal_type: s.meal_type,
            servings: s.servings,
            estimated_minutes: s.estimated_minutes,
            difficulty: s.difficulty,
            ingredients: s.ingredients.length
              ? s.ingredients
              : s.ingredients_used.map((name) => ({ name, quantity: '' })),
            steps: s.steps,
            tips: s.tips,
            prep_minutes: s.prep_minutes,
            cook_minutes: s.cook_minutes,
            image: s.image,
          },
        },
        { params: { lang: IDIOMA } },
      )
    ).data,
  updateNotes: async (id: number, notes: string) =>
    (await api.patch<Favorite>(`/favorites/${id}/`, { notes }, { params: { lang: IDIOMA } })).data,
  remove: async (id: number) => {
    await api.delete(`/favorites/${id}/`)
  },
}

// --- IA ---

export const aiApi = {
  suggestions: async (ingredientes: string[], tipoComida = '', consulta = '', maxResults = 3) =>
    (
      await api.post<{ suggestions: AiSuggestion[] }>(
        '/ai/suggestions/',
        {
          ingredients: ingredientes,
          max_results: maxResults,
          meal_type: tipoComida,
          query: consulta,
        },
        { timeout: TIEMPO_IA },
      )
    ).data.suggestions,
  adaptRecipe: async (
    receta: Pick<Recipe, 'title' | 'ingredients'> & Partial<Recipe>,
    disponibles: string[],
  ) =>
    (
      await api.post<AiAdaptation>(
        '/ai/adapt-recipe/',
        {
          recipe: {
            title: receta.title,
            ingredients: receta.ingredients,
            instructions: receta.instructions ?? '',
          },
          available_ingredients: disponibles,
        },
        { timeout: TIEMPO_IA },
      )
    ).data,
}

// --- Dieta semanal ---

export const mealPlansApi = {
  list: async () => (await api.get<MealPlan[]>('/meal-plans/')).data,
  /** La IA genera la dieta de la semana y el servidor la guarda. Tarda: es una respuesta larga. */
  generate: async (opciones: OpcionesPlan) =>
    (await api.post<MealPlan>('/ai/meal-plan/', opciones, { timeout: TIEMPO_IA })).data,
  remove: async (id: number) => {
    await api.delete(`/meal-plans/${id}/`)
  },
}

// --- Catálogo de platos ---

export const dishesApi = {
  list: async (filtros: FiltrosPlatos = {}) =>
    (await api.get<{ count: number; results: Plato[] }>('/dishes/', { params: filtros })).data,
  countries: async () =>
    (await api.get<{ country: string; total: number }[]>('/dishes/countries/')).data,
}
