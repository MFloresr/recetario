import { afterEach, describe, expect, it } from 'vitest'
import AiSuggestionsDialog from '@/components/AiSuggestionsDialog.vue'
import { montar } from '@/test/utils'
import type { AiSuggestion } from '@/types/api'

const tortilla: AiSuggestion = {
  title: 'Tortilla de patatas',
  description: 'Clásico de la cocina española',
  meal_type: 'almuerzo',
  servings: 4,
  ingredients: [
    { name: 'huevos', quantity: '6' },
    { name: 'patatas', quantity: '600 g' },
  ],
  ingredients_used: ['huevos'],
  missing_ingredients: ['patatas'],
  steps: ['Pela las patatas', 'Fríelas'],
  estimated_minutes: 75,
  difficulty: 'fácil',
  image: {
    url: 'https://upload.wikimedia.org/t.jpg',
    credit: 'Wikipedia',
    page: 'https://es.wikipedia.org/wiki/Tortilla_de_patatas',
  },
}

let montado: { unmount: () => void } | null = null

afterEach(() => {
  montado?.unmount()
  montado = null
  document.body.innerHTML = ''
})

async function montarDialogo(sugerencias: AiSuggestion[], extra: Record<string, unknown> = {}) {
  const resultado = await montar(AiSuggestionsDialog, {
    props: { modelValue: true, sugerencias, cargando: false, error: '', ...extra },
    attachTo: document.body,
  })
  montado = resultado.wrapper
  return resultado
}

describe('AiSuggestionsDialog', () => {
  it('muestra tipo de comida, tiempo, dificultad y raciones', async () => {
    await montarDialogo([tortilla])
    const texto = document.body.textContent ?? ''
    expect(texto).toContain('Tortilla de patatas')
    expect(texto).toContain('Almuerzo')
    expect(texto).toContain('1 h 15 min')
    expect(texto).toContain('Dificultad fácil')
    expect(texto).toContain('4 raciones')
  })

  it('muestra la foto con su autoría y avisa de que la receta es de una IA', async () => {
    await montarDialogo([tortilla])
    expect(
      document.body.querySelector('a[href="https://es.wikipedia.org/wiki/Tortilla_de_patatas"]')
        ?.textContent,
    ).toBe('Wikipedia')
    expect(document.body.textContent).toContain('Recetas generadas por una IA')
  })

  it('sin foto no pinta imagen ni autoría', async () => {
    await montarDialogo([{ ...tortilla, image: null }])
    expect(document.body.textContent).not.toContain('Foto orientativa')
  })

  it('permite elegir el tipo de comida', async () => {
    await montarDialogo([tortilla])
    const etiquetas = [...document.body.querySelectorAll('.v-chip-group .v-chip')].map((c) =>
      c.textContent?.trim(),
    )
    expect(etiquetas).toEqual(
      expect.arrayContaining(['Cualquiera', 'Desayuno', 'Postre', 'Batido']),
    )
  })

  it('el botón de faltantes avisa con la receta', async () => {
    const { wrapper } = await montarDialogo([tortilla])
    const boton = [...document.body.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Añadir lo que falta'),
    )
    boton?.click()
    expect(wrapper.emitted('añadir-faltantes')?.[0]?.[0]).toMatchObject({
      title: 'Tortilla de patatas',
    })
  })

  it('muestra el error y deja reintentar', async () => {
    const { wrapper } = await montarDialogo([], {
      error: 'La IA no está configurada en el servidor.',
    })
    expect(document.body.textContent).toContain('La IA no está configurada')
    const reintentar = [...document.body.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Reintentar'),
    )
    reintentar?.click()
    expect(wrapper.emitted('reintentar')).toHaveLength(1)
  })
})
