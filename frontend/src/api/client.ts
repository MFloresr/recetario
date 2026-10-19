import axios from 'axios'

/**
 * Cliente HTTP del frontend. Solo habla con la API de Django: nunca con TheMealDB ni con la IA.
 * Los interceptores de JWT y el refresco de token llegan en la fase 2.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  timeout: 15_000,
})

export interface EstadoApi {
  status: string
}

export async function comprobarApi(): Promise<EstadoApi> {
  const { data } = await api.get<EstadoApi>('/health/')
  return data
}
