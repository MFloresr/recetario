import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { dishesApi } from '@/api/endpoints'
import { montar } from '@/test/utils'
import type { Plato } from '@/types/api'
import ExploreView from '@/views/ExploreView.vue'

vi.mock('@/api/endpoints', () => ({
  dishesApi: { list: vi.fn(), countries: vi.fn() },
}))

function plato(id: number, nombre: string): Plato {
  return {
    id,
    name_es: nombre,
    name_en: '',
    description: '',
    country: 'ES',
    meal_type: '',
    diets: ['vegano'],
    ingredients: [],
    steps: '',
    calories: 300,
    image: '',
    image_credit: '',
    image_license: '',
    reviewed: false,
    source: 'wikidata',
  }
}

describe('ExploreView', () => {
  beforeEach(() => {
    vi.mocked(dishesApi.countries).mockResolvedValue([{ country: 'ES', total: 2 }])
    vi.mocked(dishesApi.list).mockResolvedValue({
      count: 2,
      results: [plato(1, 'Gazpacho'), plato(2, 'Paella')],
    })
  })

  it('muestra los platos del catálogo con su dieta', async () => {
    const { wrapper: w } = await montar(ExploreView)
    await flushPromises()
    expect(w.text()).toContain('Gazpacho')
    expect(w.text()).toContain('Paella')
    expect(w.text()).toContain('vegano')
    expect(w.text()).toContain('2 platos')
  })

  it('avisa cuando no hay resultados', async () => {
    vi.mocked(dishesApi.list).mockResolvedValue({ count: 0, results: [] })
    const { wrapper: w } = await montar(ExploreView)
    await flushPromises()
    expect(w.text()).toContain('No hay platos con esos filtros')
  })
})
