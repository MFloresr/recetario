import { describe, expect, it } from 'vitest'
import RecipeCard from '@/components/RecipeCard.vue'
import { montar } from '@/test/utils'
import type { RecipeSummary } from '@/types/api'

const receta: RecipeSummary = {
  external_id: '52772',
  title: 'Chicken Handi',
  image: 'https://example.com/handi.jpg',
  category: 'Chicken',
  area: 'Indian',
  match_score: 80,
  matched_ingredients: ['chicken', 'rice', 'onion', 'garlic'],
  missing_ingredients: ['yogurt'],
  source: 'themealdb',
}

describe('RecipeCard', () => {
  it('muestra título, origen, porcentaje y listas de ingredientes', async () => {
    const { wrapper } = await montar(RecipeCard, { props: { receta, favorita: false } })
    const texto = wrapper.text()
    expect(texto).toContain('Chicken Handi')
    expect(texto).toContain('Chicken · Indian')
    expect(texto).toContain('80% de ingredientes disponibles')
    expect(texto).toContain('Tienes: chicken, rice, onion, garlic')
    expect(texto).toContain('Te falta: yogurt')
  })

  it('enlaza al detalle de la receta', async () => {
    const { wrapper } = await montar(RecipeCard, { props: { receta, favorita: false } })
    const enlace = wrapper.find('a[href="/recipes/52772"]')
    expect(enlace.exists()).toBe(true)
    expect(enlace.text()).toContain('Ver receta')
  })

  it('el botón de favorito refleja el estado y avisa al pulsarlo', async () => {
    const { wrapper } = await montar(RecipeCard, { props: { receta, favorita: true } })
    const boton = wrapper.find('button[aria-label="Quitar de favoritos"]')
    expect(boton.attributes('aria-pressed')).toBe('true')
    await boton.trigger('click')
    expect(wrapper.emitted('alternar-favorito')).toHaveLength(1)
  })

  it('si no falta nada lo dice', async () => {
    const completa = {
      ...receta,
      match_score: 100,
      matched_ingredients: ['rice'],
      missing_ingredients: [],
    }
    const { wrapper } = await montar(RecipeCard, { props: { receta: completa, favorita: false } })
    expect(wrapper.text()).toContain('¡No te falta nada!')
    expect(wrapper.text()).not.toContain('Te falta:')
  })

  it('resume las listas largas', async () => {
    const larga = { ...receta, missing_ingredients: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] }
    const { wrapper } = await montar(RecipeCard, { props: { receta: larga, favorita: false } })
    expect(wrapper.text()).toContain('a, b, c, d, e, f y 2 más')
  })
})
