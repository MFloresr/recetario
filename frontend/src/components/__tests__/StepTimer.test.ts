import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StepTimer from '@/components/StepTimer.vue'
import { montar } from '@/test/utils'

const boton = (wrapper: Awaited<ReturnType<typeof montar>>['wrapper'], etiqueta: string) =>
  wrapper.find(`button[aria-label="${etiqueta}"]`)

describe('StepTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Object.defineProperty(navigator, 'vibrate', { value: vi.fn(), configurable: true })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('muestra los minutos del paso y un botón para iniciar', async () => {
    const { wrapper } = await montar(StepTimer, { props: { minutos: 15 } })
    expect(wrapper.text()).toContain('15 min')
    expect(boton(wrapper, 'Iniciar temporizador de 15 minutos').exists()).toBe(true)
  })

  it('cuenta atrás en minutos y segundos', async () => {
    const { wrapper } = await montar(StepTimer, { props: { minutos: 2 } })
    await boton(wrapper, 'Iniciar temporizador de 2 minutos').trigger('click')
    expect(wrapper.find('.tiempo').text()).toBe('02:00')
    await vi.advanceTimersByTimeAsync(61_000)
    expect(wrapper.find('.tiempo').text()).toBe('00:59')
  })

  it('se puede pausar y seguir', async () => {
    const { wrapper } = await montar(StepTimer, { props: { minutos: 1 } })
    await boton(wrapper, 'Iniciar temporizador de 1 minutos').trigger('click')
    await vi.advanceTimersByTimeAsync(10_000)
    await boton(wrapper, 'Pausar el temporizador').trigger('click')
    await vi.advanceTimersByTimeAsync(30_000) // en pausa no avanza
    expect(wrapper.text()).toContain('Seguir 00:50')
  })

  it('al llegar a cero avisa y vibra', async () => {
    const { wrapper } = await montar(StepTimer, { props: { minutos: 1 } })
    await boton(wrapper, 'Iniciar temporizador de 1 minutos').trigger('click')
    await vi.advanceTimersByTimeAsync(60_000)
    expect(wrapper.text()).toContain('¡Tiempo cumplido!')
    expect(navigator.vibrate).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Repetir')
  })

  it('reiniciar vuelve al tiempo completo', async () => {
    const { wrapper } = await montar(StepTimer, { props: { minutos: 1 } })
    await boton(wrapper, 'Iniciar temporizador de 1 minutos').trigger('click')
    await vi.advanceTimersByTimeAsync(20_000)
    await boton(wrapper, 'Pausar el temporizador').trigger('click')
    await boton(wrapper, 'Reiniciar el temporizador').trigger('click')
    expect(wrapper.text()).toContain('1 min')
    expect(wrapper.text()).not.toContain('Seguir')
  })
})
