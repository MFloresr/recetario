import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useUiStore } from '@/stores/ui'

describe('useUiStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('guarda el tema elegido', () => {
    const ui = useUiStore()
    ui.elegirTema('dark')
    expect(ui.tema).toBe('dark')
    expect(localStorage.getItem('recetario-tema')).toBe('dark')
  })

  it('muestra un aviso con su color', () => {
    const ui = useUiStore()
    ui.mostrarAviso('Guardado', 'success')
    expect(ui.aviso).toEqual({ visible: true, texto: 'Guardado', color: 'success' })
  })

  it('cuenta las peticiones sin bajar de cero', () => {
    const ui = useUiStore()
    ui.empezarPeticion()
    ui.terminarPeticion()
    ui.terminarPeticion()
    expect(ui.peticiones).toBe(0)
  })
})
