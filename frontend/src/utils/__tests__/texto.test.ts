import { describe, expect, it } from 'vitest'
import { agruparPorCategoria } from '@/utils/catalogo'
import { normalizar, pasosDeInstrucciones } from '@/utils/texto'

describe('texto', () => {
  it('normaliza sin tildes ni mayúsculas', () => {
    expect(normalizar('  Jamón Serrano ')).toBe('jamon serrano')
  })

  it('divide las instrucciones en pasos y descarta rótulos «STEP n»', () => {
    const pasos = pasosDeInstrucciones('STEP 1\r\nCorta la cebolla.\r\n\r\nSTEP 2\r\nSofríela.')
    expect(pasos).toEqual(['Corta la cebolla.', 'Sofríela.'])
  })
})

describe('agruparPorCategoria', () => {
  it('respeta el orden de categorías y manda lo sin categoría a «Otros»', () => {
    const grupos = agruparPorCategoria([
      { category: 'carne' as const, name: 'pollo' },
      { category: '' as const, name: 'cosa' },
      { category: 'verdura' as const, name: 'ajo' },
    ])
    expect(grupos.map((g) => g.valor)).toEqual(['verdura', 'carne', 'otro'])
    expect(grupos[2]!.items[0]!.name).toBe('cosa')
  })
})
