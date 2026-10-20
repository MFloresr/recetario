import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { aiApi, mealPlansApi } from '@/api/endpoints'
import { montar } from '@/test/utils'
import type { MealPlan } from '@/types/api'
import MealPlanView from '@/views/MealPlanView.vue'

vi.mock('@/api/endpoints', () => ({
  mealPlansApi: { list: vi.fn(), generate: vi.fn(), remove: vi.fn() },
  aiApi: { suggestions: vi.fn() },
  pantryApi: {},
  ingredientsApi: { list: vi.fn().mockResolvedValue([]) },
  favoritesApi: { list: vi.fn().mockResolvedValue([]) },
}))

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

function plan(id = 1, titulo = 'Semana ligera'): MealPlan {
  return {
    id,
    title: titulo,
    notes: 'Bebe agua entre comidas',
    created_at: '2026-10-19T10:00:00Z',
    options: {
      goal: 'bajar de peso',
      meals: [],
      calories: 1800,
      diet: 'mediterránea',
      avoid: [],
      use_pantry: false,
    },
    days: DIAS.map((day, i) => ({
      day,
      meals: [
        {
          type: 'desayuno',
          title: `Tostadas ${i}`,
          description: 'Con tomate',
          calories: 300,
          ingredients: ['pan', 'tomate'],
        },
        {
          type: 'cena',
          title: 'Tortilla francesa',
          description: '',
          calories: 400,
          ingredients: [],
        },
      ],
    })),
  }
}

describe('MealPlanView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sin dietas invita a crear la primera', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([])
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    expect(wrapper.text()).toContain('Todavía no tienes ninguna dieta')
    expect(wrapper.text()).toContain('Generar mi dieta de la semana')
  })

  it('pinta los 7 días con sus comidas, calorías y el consejo', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([plan()])
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    const tarjetas = wrapper.findAll('.dia')
    expect(tarjetas).toHaveLength(7)
    expect(tarjetas[0]!.text()).toContain('Lunes')
    expect(tarjetas[0]!.text()).toContain('700 kcal') // 300 + 400
    expect(tarjetas[0]!.text()).toContain('Tostadas 0')
    expect(wrapper.text()).toContain('Semana ligera')
    expect(wrapper.text()).toContain('Bebe agua entre comidas')
    expect(wrapper.findAll('.comida')).toHaveLength(14)
  })

  it('resalta el día de hoy', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([plan()])
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    expect(wrapper.findAll('.dia-hoy')).toHaveLength(1)
  })

  it('genera la dieta con las opciones elegidas y la muestra', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([])
    vi.mocked(mealPlansApi.generate).mockResolvedValue(plan(7, 'Mi semana'))
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(mealPlansApi.generate).toHaveBeenCalledWith(
      expect.objectContaining({
        goal: 'mantener el peso',
        meals: ['desayuno', 'almuerzo', 'merienda', 'cena'],
        calories: null,
        use_pantry: false,
      }),
    )
    expect(wrapper.text()).toContain('Mi semana')
    expect(wrapper.findAll('.dia')).toHaveLength(7)
  })

  it('si la IA falla muestra el error y no rompe la pantalla', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([])
    vi.mocked(mealPlansApi.generate).mockRejectedValue(new Error('La IA está saturada'))
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('La IA está saturada')
    expect(wrapper.findAll('.dia')).toHaveLength(0)
  })

  it('«Ver receta» pide la receta a la IA una sola vez y abre su detalle', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([plan()])
    vi.mocked(aiApi.suggestions).mockResolvedValue([
      { title: 'Tostadas 0', external_id: 'ai-1-abc', saved: true } as never,
    ])
    const { wrapper, router } = await montar(MealPlanView)
    await flushPromises()
    const boton = wrapper
      .findAll('.dia')[0]!
      .findAll('button')
      .find((b) => b.text().includes('Ver receta'))!
    await boton.trigger('click')
    await flushPromises()
    expect(aiApi.suggestions).toHaveBeenCalledWith(['pan', 'tomate'], '', 'Tostadas 0', 1)
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/recipes/ai-1-abc'))
  })

  it('no deja generar con menos de dos comidas', async () => {
    vi.mocked(mealPlansApi.list).mockResolvedValue([])
    const { wrapper } = await montar(MealPlanView)
    await flushPromises()
    const chips = wrapper.findAll('.v-chip-group .v-chip')
    await chips[0]!.trigger('click')
    await chips[1]!.trigger('click')
    await chips[2]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Elige al menos dos comidas al día')
  })
})
