import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { aiApi, favoritesApi } from '@/api/endpoints'
import { useRecipeStore } from '@/stores/recipe'
import type { AiSuggestion, Favorite } from '@/types/api'

vi.mock('@/api/endpoints', () => ({
  aiApi: { suggestions: vi.fn(), adaptRecipe: vi.fn() },
  favoritesApi: {
    createFromAi: vi.fn(),
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    updateNotes: vi.fn(),
  },
  recipesApi: { suggestions: vi.fn(), detail: vi.fn() },
}))

const tortilla: AiSuggestion = {
  title: 'Tortilla de patatas',
  description: '',
  meal_type: 'almuerzo',
  servings: 4,
  ingredients: [{ name: 'huevos', quantity: '6' }],
  ingredients_used: [],
  missing_ingredients: [],
  steps: ['Cuaja la tortilla'],
  estimated_minutes: 45,
  difficulty: 'fácil',
  image: null,
}

describe('useRecipeStore (recetas de la IA)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('guarda una receta de la IA y la añade a los favoritos', async () => {
    const guardada = {
      id: 7,
      notes: '',
      created_at: '',
      recipe: { external_id: 'ai-1-abc', source: 'ai', title: 'Tortilla de patatas' },
    } as Favorite
    vi.mocked(favoritesApi.createFromAi).mockResolvedValue(guardada)
    const recetas = useRecipeStore()
    await recetas.guardarRecetaIa(tortilla)
    expect(favoritesApi.createFromAi).toHaveBeenCalledWith(tortilla)
    expect(recetas.favoritos).toEqual([guardada])
    expect(recetas.esFavorito('ai-1-abc')).toBe(true)
  })

  it('pide a la IA ingredientes, tipo de comida y búsqueda de texto', async () => {
    vi.mocked(aiApi.suggestions).mockResolvedValue([tortilla])
    const recetas = useRecipeStore()
    await recetas.pedirSugerenciasIa(['huevo'], 'almuerzo', 'tortilla')
    expect(aiApi.suggestions).toHaveBeenCalledWith(['huevo'], 'almuerzo', 'tortilla')
    expect(recetas.sugerenciasIa).toEqual([tortilla])
  })

  it('si guardar falla muestra el error y no cambia los favoritos', async () => {
    vi.mocked(favoritesApi.createFromAi).mockRejectedValue(
      new Error('Esta receta ya está en tus favoritos.'),
    )
    const recetas = useRecipeStore()
    await expect(recetas.guardarRecetaIa(tortilla)).rejects.toThrow('ya está en tus favoritos')
    expect(recetas.favoritos).toEqual([])
  })
})
