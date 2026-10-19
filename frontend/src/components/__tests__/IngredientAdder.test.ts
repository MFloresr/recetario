import { describe, expect, it } from 'vitest'
import IngredientAdder from '@/components/IngredientAdder.vue'
import { montar } from '@/test/utils'

describe('IngredientAdder', () => {
  it('añade lo escrito al enviar el formulario y vacía el campo', async () => {
    const { wrapper } = await montar(IngredientAdder)
    const campo = wrapper.find('input')
    await campo.setValue('  Tomate cherry ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('añadir')).toEqual([['Tomate cherry']])
    expect((campo.element as HTMLInputElement).value).toBe('')
  })

  it('escribir no añade nada hasta confirmar', async () => {
    const { wrapper } = await montar(IngredientAdder)
    await wrapper.find('input').setValue('pol')
    expect(wrapper.emitted('añadir')).toBeUndefined()
  })

  it('no envía textos vacíos', async () => {
    const { wrapper } = await montar(IngredientAdder)
    await wrapper.find('input').setValue('   ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('añadir')).toBeUndefined()
  })

  it('sugiere ingredientes frecuentes filtrados por lo escrito y sin repetir los que ya tienes', async () => {
    const { wrapper } = await montar(IngredientAdder, { props: { existentes: ['Pimiento'] } })
    await wrapper.find('input').setValue('pim')
    const sugeridos = wrapper.findAll('.v-chip').map((c) => c.text())
    expect(sugeridos).toEqual(['pimienta'])
  })

  it('pulsar una sugerencia la añade', async () => {
    const { wrapper } = await montar(IngredientAdder)
    const chip = wrapper.findAll('.v-chip').find((c) => c.text() === 'arroz')!
    await chip.trigger('click')
    expect(wrapper.emitted('añadir')).toEqual([['arroz']])
  })
})
