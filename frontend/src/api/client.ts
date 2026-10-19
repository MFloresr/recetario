import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useUiStore } from '@/stores/ui'
import { borrarTokens, guardarTokens, leerTokens } from './tokens'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** No cuenta para el indicador de carga global (p. ej. comprobaciones en segundo plano). */
    _sinCarga?: boolean
  }
}

/**
 * Cliente HTTP del frontend. Solo habla con la API de Django: nunca con TheMealDB ni con la IA.
 * Añade el JWT, lo refresca cuando caduca y convierte los errores en mensajes legibles.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  timeout: 20_000,
})

/** Lo registra el store de sesión: se llama cuando ya no hay forma de renovar la sesión. */
let alCerrarSesion: () => void = () => {}
export function registrarCierreDeSesion(callback: () => void): void {
  alCerrarSesion = callback
}

type Peticion = InternalAxiosRequestConfig & { _reintentada?: boolean }

function medirCarga(accion: 'empezar' | 'terminar') {
  const ui = useUiStore()
  if (accion === 'empezar') ui.empezarPeticion()
  else ui.terminarPeticion()
}

api.interceptors.request.use((config: Peticion) => {
  const tokens = leerTokens()
  if (tokens?.access) config.headers.Authorization = `Bearer ${tokens.access}`
  if (!config._sinCarga) medirCarga('empezar')
  return config
})

// Una sola renovación a la vez: si varias peticiones caducan juntas, esperan a la misma
let renovando: Promise<string> | null = null

async function renovarAcceso(): Promise<string> {
  const tokens = leerTokens()
  if (!tokens?.refresh) throw new Error('Sin refresh token')
  // Petición directa (sin interceptores) para no entrar en bucle
  const { data } = await axios.post<{ access: string; refresh?: string }>(
    `${api.defaults.baseURL}/auth/token/refresh/`,
    { refresh: tokens.refresh },
    { timeout: 15_000 },
  )
  guardarTokens({ access: data.access, refresh: data.refresh ?? tokens.refresh })
  return data.access
}

api.interceptors.response.use(
  (respuesta) => {
    if (!(respuesta.config as Peticion)._sinCarga) medirCarga('terminar')
    return respuesta
  },
  async (error: AxiosError) => {
    const config = error.config as Peticion | undefined
    if (config && !config._sinCarga) medirCarga('terminar')

    const esLogin =
      config?.url?.includes('/auth/login/') || config?.url?.includes('/auth/register/')
    if (error.response?.status === 401 && config && !config._reintentada && !esLogin) {
      config._reintentada = true
      try {
        renovando ??= renovarAcceso().finally(() => {
          renovando = null
        })
        const nuevo = await renovando
        config.headers.Authorization = `Bearer ${nuevo}`
        return api(config)
      } catch {
        borrarTokens()
        alCerrarSesion()
      }
    }
    return Promise.reject(error)
  },
)

/** Error de la API con un mensaje listo para mostrar al usuario. */
export class ApiError extends Error {
  status: number | null
  code: string | null
  fields: Record<string, string>

  constructor(
    message: string,
    status: number | null = null,
    code: string | null = null,
    fields: Record<string, string> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

function aTexto(valor: unknown): string {
  if (Array.isArray(valor)) return valor.map(aTexto).join(' ')
  if (valor && typeof valor === 'object') return Object.values(valor).map(aTexto).join(' ')
  return String(valor ?? '')
}

/** Convierte cualquier fallo de red o de la API en un ApiError con texto claro en español. */
export function aApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      const agotado = error.code === 'ECONNABORTED'
      return new ApiError(
        agotado
          ? 'El servidor tardó demasiado en responder. Inténtalo de nuevo.'
          : 'No se pudo conectar con el servidor. Revisa tu conexión.',
        null,
        agotado ? 'timeout' : 'network',
      )
    }
    const { status, data } = error.response
    if (status === 401)
      return new ApiError(
        'Tu sesión ha caducado o los datos no son correctos.',
        status,
        'unauthorized',
      )
    if (status === 429)
      return new ApiError(
        'Has hecho demasiadas peticiones. Espera un poco y vuelve a intentarlo.',
        status,
        'throttled',
      )
    if (data && typeof data === 'object') {
      const cuerpo = data as Record<string, unknown>
      if (typeof cuerpo.detail === 'string')
        return new ApiError(cuerpo.detail, status, (cuerpo.code as string) ?? null)
      const campos: Record<string, string> = {}
      for (const [clave, valor] of Object.entries(cuerpo)) campos[clave] = aTexto(valor)
      const primero = Object.values(campos)[0]
      if (primero) return new ApiError(primero, status, null, campos)
    }
    if (status >= 500)
      return new ApiError('Ha ocurrido un error en el servidor. Inténtalo más tarde.', status)
    return new ApiError('No se pudo completar la acción.', status)
  }
  return new ApiError(error instanceof Error ? error.message : 'Error desconocido')
}
