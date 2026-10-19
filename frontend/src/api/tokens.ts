import type { Tokens } from '@/types/api'

const KEY = 'recetario-tokens'

/** Los tokens viven en localStorage; si no está disponible (modo privado) solo duran la sesión de la pestaña. */
let enMemoria: Tokens | null = null

export function leerTokens(): Tokens | null {
  if (enMemoria) return enMemoria
  try {
    const crudo = localStorage.getItem(KEY)
    if (crudo) enMemoria = JSON.parse(crudo) as Tokens
  } catch {
    enMemoria = null
  }
  return enMemoria
}

export function guardarTokens(tokens: Tokens): void {
  enMemoria = tokens
  try {
    localStorage.setItem(KEY, JSON.stringify(tokens))
  } catch {
    // Sin localStorage: se mantiene solo en memoria
  }
}

export function borrarTokens(): void {
  enMemoria = null
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Nada que borrar
  }
}
