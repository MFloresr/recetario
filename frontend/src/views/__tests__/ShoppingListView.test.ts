import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { shoppingApi } from '@/api/endpoints'
import { montar } from '@/test/utils'
import type { ShoppingItem } from '@/types/api'
import ShoppingListView from '@/views/ShoppingListView.vue'

vi.mock('@/api/endpoints', () => ({
  shoppingApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    clearBought: vi.fn(),
  },
}))

function item(
  id: number,
  name: string,
  category: ShoppingItem['category'],
  bought = false,
): ShoppingItem {
  return {
    id,
    name,
    normalized_name: name.toLowerCase(),
    quantity: '',
    category,
    bought,
    created_at: '',
  }
}

describe('ShoppingListView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('agrupa por categoría y cuenta los pendientes', async () => {
    vi.mocked(shoppingApi.list).mockResolvedValue([
      item(1, 'Leche', 'lacteo'),
      item(2, 'Pan', 'cereal', true),
      item(3, 'Pollo', 'carne'),
    ])
    const { wrapper } = await montar(ShoppingListView)
    await flushPromises()
    const texto = wrapper.text()
    expect(texto).toContain('Lácteos')
    expect(texto).toContain('Cereales y pasta')
    expect(texto).toContain('Carnes y huevos')
    expect(wrapper.find('.pendientes').text()).toContain('2 pendientes')
    expect(texto).toContain('Eliminar comprados (1)')
  })

  it('muestra el estado vacío', async () => {
    vi.mocked(shoppingApi.list).mockResolvedValue([])
    const { wrapper } = await montar(ShoppingListView)
    await flushPromises()
    expect(wrapper.text()).toContain('Tu lista de la compra está vacía')
    expect(wrapper.find('.pendientes').exists()).toBe(false)
  })

  it('marcar un producto como comprado lo guarda en la API', async () => {
    vi.mocked(shoppingApi.list).mockResolvedValue([item(1, 'Leche', 'lacteo')])
    vi.mocked(shoppingApi.update).mockResolvedValue(item(1, 'Leche', 'lacteo', true))
    const { wrapper } = await montar(ShoppingListView)
    await flushPromises()
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await flushPromises()
    expect(shoppingApi.update).toHaveBeenCalledWith(1, { bought: true })
    expect(wrapper.find('.pendientes').text()).toContain('0 pendientes')
  })

  it('añade un producto nuevo', async () => {
    vi.mocked(shoppingApi.list).mockResolvedValue([])
    vi.mocked(shoppingApi.create).mockResolvedValue(item(9, 'Sal', 'especia'))
    const { wrapper } = await montar(ShoppingListView)
    await flushPromises()
    await wrapper.find('input').setValue('Sal')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(shoppingApi.create).toHaveBeenCalledWith('Sal', '')
    expect(wrapper.text()).toContain('Sal')
  })
})
