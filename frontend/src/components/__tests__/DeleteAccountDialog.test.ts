import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '@/api/endpoints'
import { guardarTokens, leerTokens } from '@/api/tokens'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import { montar } from '@/test/utils'

vi.mock('@/api/endpoints', () => ({
  authApi: { deleteAccount: vi.fn(), login: vi.fn(), me: vi.fn(), register: vi.fn() },
}))

let montado: { unmount: () => void } | null = null

afterEach(() => {
  montado?.unmount()
  montado = null
  document.body.innerHTML = ''
})

async function abrir() {
  const r = await montar(DeleteAccountDialog, {
    props: { modelValue: true },
    attachTo: document.body,
  })
  montado = r.wrapper
  await flushPromises()
  return r
}

const boton = (texto: string) =>
  [...document.body.querySelectorAll('button')].find((b) => b.textContent?.includes(texto))

describe('DeleteAccountDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    guardarTokens({ access: 'a', refresh: 'r' })
  })

  it('avisa de lo que se borra', async () => {
    await abrir()
    expect(document.body.textContent).toContain(
      'tu despensa, tu lista de la compra y tus favoritos',
    )
    expect(document.body.textContent).toContain('No se puede deshacer')
  })

  it('no borra nada sin contraseña', async () => {
    await abrir()
    boton('Eliminar cuenta')?.click()
    await flushPromises()
    expect(authApi.deleteAccount).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Escribe tu contraseña para confirmar')
  })

  it('con la contraseña borra la cuenta, cierra la sesión y avisa', async () => {
    vi.mocked(authApi.deleteAccount).mockResolvedValue()
    const { wrapper } = await abrir()
    const campo = document.body.querySelector('input[type="password"]') as HTMLInputElement
    campo.value = 'Contrasena-Segura-91'
    campo.dispatchEvent(new Event('input'))
    boton('Eliminar cuenta')?.click()
    await flushPromises()
    expect(authApi.deleteAccount).toHaveBeenCalledWith('Contrasena-Segura-91')
    expect(wrapper.emitted('eliminada')).toHaveLength(1)
    expect(leerTokens()).toBeNull()
  })

  it('si la contraseña es incorrecta muestra el error y conserva la sesión', async () => {
    vi.mocked(authApi.deleteAccount).mockRejectedValue(new Error('La contraseña no es correcta.'))
    const { wrapper } = await abrir()
    const campo = document.body.querySelector('input[type="password"]') as HTMLInputElement
    campo.value = 'mala'
    campo.dispatchEvent(new Event('input'))
    boton('Eliminar cuenta')?.click()
    await flushPromises()
    expect(document.body.textContent).toContain('La contraseña no es correcta.')
    expect(wrapper.emitted('eliminada')).toBeUndefined()
    expect(leerTokens()).not.toBeNull()
  })
})
