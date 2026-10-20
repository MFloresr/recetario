import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '@/api/endpoints'
import { borrarTokens } from '@/api/tokens'
import { montar } from '@/test/utils'
import RegisterView from '@/views/RegisterView.vue'

vi.mock('@/api/endpoints', () => ({
  authApi: { login: vi.fn(), me: vi.fn(), register: vi.fn(), deleteAccount: vi.fn() },
}))

async function rellenar(wrapper: Awaited<ReturnType<typeof montar>>['wrapper']) {
  const campos = wrapper.findAll('input:not([type="checkbox"])')
  await campos[0]!.setValue('ana@example.com')
  await campos[1]!.setValue('ana')
  await campos[2]!.setValue('Contrasena-Segura-91')
}

describe('RegisterView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    borrarTokens()
    localStorage.clear()
  })

  it('enlaza al aviso de privacidad', async () => {
    const { wrapper } = await montar(RegisterView)
    expect(wrapper.text()).toContain('aviso de privacidad')
  })

  it('no crea la cuenta si no se acepta el aviso de privacidad', async () => {
    const { wrapper } = await montar(RegisterView)
    await rellenar(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.register).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain('aceptar el aviso de privacidad')
  })

  it('con el aviso aceptado crea la cuenta e inicia sesión', async () => {
    vi.mocked(authApi.register).mockResolvedValue({
      id: 1,
      email: 'ana@example.com',
      username: 'ana',
    })
    vi.mocked(authApi.login).mockResolvedValue({ access: 'a', refresh: 'r' })
    vi.mocked(authApi.me).mockResolvedValue({ id: 1, email: 'ana@example.com', username: 'ana' })
    const { wrapper, router } = await montar(RegisterView)
    await rellenar(wrapper)
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.register).toHaveBeenCalledWith({
      email: 'ana@example.com',
      username: 'ana',
      password: 'Contrasena-Segura-91',
    })
    expect(router.currentRoute.value.name).toBe('home')
  })
})
