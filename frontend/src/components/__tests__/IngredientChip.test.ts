import { describe, expect, it } from 'vitest'
import IngredientChip from '@/components/IngredientChip.vue'
import { montar } from '@/test/utils'

describe('IngredientChip', () => {
  it('muestra el nombre y la cantidad', async () => {
    const { wrapper } = await montar(IngredientChip, {
      props: { nombre: 'pollo', cantidad: '500 g' },
    })
    expect(wrapper.text()).toContain('pollo')
    expect(wrapper.text()).toContain('500 g')
  })

  it('sin cantidad solo muestra el nombre', async () => {
    const { wrapper } = await montar(IngredientChip, { props: { nombre: 'arroz' } })
    expect(wrapper.text().trim()).toBe('arroz')
  })

  it('avisa al cerrar con el botón de quitar', async () => {
    const { wrapper } = await montar(IngredientChip, { props: { nombre: 'ajo' } })
    await wrapper.find('.v-chip__close').trigger('click')
    expect(wrapper.emitted('quitar')).toHaveLength(1)
  })
})
