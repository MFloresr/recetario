import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '@/api/endpoints'
import { borrarTokens } from '@/api/tokens'
import { montar } from '@/test/utils'
import LoginView from '@/views/LoginView.vue'

vi.mock('@/api/endpoints', () => ({
  authApi: { login: vi.fn(), me: vi.fn(), register: vi.fn() },
}))

async function escribir(
  wrapper: Awaited<ReturnType<typeof montar>>['wrapper'],
  usuario: string,
  clave: string,
) {
  const campos = wrapper.findAll('input')
  await campos[0]!.setValue(usuario)
  await campos[1]!.setValue(clave)
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    borrarTokens()
    localStorage.clear()
  })

  it('muestra el formulario con correo/usuario y contraseña', async () => {
    const { wrapper } = await montar(LoginView)
    expect(wrapper.text()).toContain('Entra en Recetario')
    expect(wrapper.findAll('input')).toHaveLength(2)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').text()).toContain('Entrar')
  })

  it('inicia sesión y va a la pantalla de inicio', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access: 'a', refresh: 'r' })
    vi.mocked(authApi.me).mockResolvedValue({ id: 1, email: 'ana@example.com', username: 'ana' })
    const { wrapper, router } = await montar(LoginView)
    await escribir(wrapper, 'ana', 'Contrasena-Segura-91')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.login).toHaveBeenCalledWith('ana', 'Contrasena-Segura-91')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('muestra el error cuando las credenciales no valen y no navega', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('Credenciales incorrectas'))
    const { wrapper, router } = await montar(LoginView)
    await escribir(wrapper, 'ana', 'mala')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Credenciales incorrectas')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('no llama a la API si faltan datos', async () => {
    const { wrapper } = await montar(LoginView)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.login).not.toHaveBeenCalled()
  })
})
