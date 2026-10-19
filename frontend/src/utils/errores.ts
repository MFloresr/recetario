import { aApiError } from '@/api/client'
import { useUiStore } from '@/stores/ui'

/** Muestra un error de la API en un snackbar y devuelve su mensaje. */
export function notificarError(error: unknown): string {
  const { message } = aApiError(error)
  useUiStore().mostrarAviso(message, 'error')
  return message
}

/** Texto de un error sin mostrarlo (para pintarlo dentro de una pantalla). */
export function mensajeDeError(error: unknown): string {
  return aApiError(error).message
}
