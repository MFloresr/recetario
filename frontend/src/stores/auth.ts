import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { aApiError, registrarCierreDeSesion } from '@/api/client'
import { authApi, type DatosRegistro } from '@/api/endpoints'
import { borrarTokens, guardarTokens, leerTokens } from '@/api/tokens'
import type { User } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const hayToken = ref(Boolean(leerTokens()))
  const cargando = ref(false)

  const autenticado = computed(() => hayToken.value)

  function cerrarSesion() {
    borrarTokens()
    hayToken.value = false
    user.value = null
  }

  // Si el refresco falla, la sesión se cierra y la app vuelve al login
  registrarCierreDeSesion(() => {
    cerrarSesion()
    window.dispatchEvent(new CustomEvent('recetario:sesion-caducada'))
  })

  async function iniciarSesion(identificador: string, password: string) {
    cargando.value = true
    try {
      guardarTokens(await authApi.login(identificador.trim(), password))
      hayToken.value = true
      user.value = await authApi.me()
    } catch (e) {
      cerrarSesion()
      throw aApiError(e)
    } finally {
      cargando.value = false
    }
  }

  async function registrar(datos: DatosRegistro) {
    cargando.value = true
    try {
      await authApi.register(datos)
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargando.value = false
    }
    await iniciarSesion(datos.username, datos.password)
  }

  /** Borra la cuenta (y todos sus datos) tras confirmar la contraseña y cierra la sesión. */
  async function eliminarCuenta(password: string) {
    try {
      await authApi.deleteAccount(password)
    } catch (e) {
      throw aApiError(e)
    }
    cerrarSesion()
  }

  /** Recupera el usuario al arrancar la app si hay tokens guardados. */
  async function cargarUsuario() {
    if (!hayToken.value || user.value) return
    try {
      user.value = await authApi.me()
    } catch {
      cerrarSesion()
    }
  }

  return {
    user,
    autenticado,
    cargando,
    iniciarSesion,
    registrar,
    eliminarCuenta,
    cerrarSesion,
    cargarUsuario,
  }
})
