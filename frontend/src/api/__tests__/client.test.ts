import { AxiosError, type AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'
import { aApiError, ApiError } from '@/api/client'

function errorHttp(status: number, data: unknown) {
  const respuesta = { status, data, statusText: '', headers: {}, config: {} } as AxiosResponse
  return new AxiosError('fallo', 'ERR_BAD_REQUEST', undefined, undefined, respuesta)
}

describe('aApiError', () => {
  it('usa el campo detail de los errores controlados del backend', () => {
    const e = aApiError(
      errorHttp(502, { detail: 'TheMealDB tardó demasiado.', code: 'themealdb_timeout' }),
    )
    expect(e.message).toBe('TheMealDB tardó demasiado.')
    expect(e.code).toBe('themealdb_timeout')
    expect(e.status).toBe(502)
  })

  it('junta los errores de validación por campo', () => {
    const e = aApiError(
      errorHttp(400, {
        email: ['Ya existe una cuenta con este correo.'],
        password: ['Demasiado corta.'],
      }),
    )
    expect(e.fields.email).toBe('Ya existe una cuenta con este correo.')
    expect(e.message).toBe('Ya existe una cuenta con este correo.')
  })

  it('traduce los errores sin respuesta', () => {
    const red = aApiError(new AxiosError('Network Error', 'ERR_NETWORK'))
    expect(red.code).toBe('network')
    expect(red.message).toContain('conectar')
    const agotado = aApiError(new AxiosError('timeout', 'ECONNABORTED'))
    expect(agotado.code).toBe('timeout')
  })

  it('mensajes genéricos para 401, 429 y 5xx', () => {
    expect(aApiError(errorHttp(401, {})).code).toBe('unauthorized')
    expect(aApiError(errorHttp(429, {})).code).toBe('throttled')
    expect(aApiError(errorHttp(500, '<html>')).message).toContain('servidor')
  })

  it('deja pasar un ApiError tal cual', () => {
    const original = new ApiError('ya listo')
    expect(aApiError(original)).toBe(original)
  })
})
