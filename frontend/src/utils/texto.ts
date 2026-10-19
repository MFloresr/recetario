/** Minúsculas y sin tildes, para comparar textos al buscar. */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .trim()
}

/** Instrucciones de TheMealDB → pasos sueltos (quita líneas vacías y rótulos como «STEP 1»). */
export function pasosDeInstrucciones(instrucciones: string): string[] {
  return instrucciones
    .split(/\r?\n+/)
    .map((linea) => linea.trim())
    .filter((linea) => linea && !/^step\s*\d+$/i.test(linea))
}
