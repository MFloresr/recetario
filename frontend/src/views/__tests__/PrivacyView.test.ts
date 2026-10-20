import { describe, expect, it } from 'vitest'
import { montar } from '@/test/utils'
import PrivacyView from '@/views/PrivacyView.vue'

describe('PrivacyView', () => {
  it('explica qué datos se guardan, con quién se comparten y cómo borrarlos', async () => {
    const { wrapper } = await montar(PrivacyView)
    const texto = wrapper.text()
    for (const frase of [
      'Aviso de privacidad',
      'Vercel',
      'Supabase',
      'Google Gemini',
      'MyMemory',
      'Eliminar mi cuenta',
      'Agencia Española de Protección de Datos',
    ]) {
      expect(texto).toContain(frase)
    }
    expect(wrapper.find('a[href^="mailto:"]').exists()).toBe(true)
  })

  it('declara que no usa cookies ni analítica', async () => {
    const { wrapper } = await montar(PrivacyView)
    expect(wrapper.text()).toContain('No usa cookies, ni analítica, ni publicidad')
  })
})
