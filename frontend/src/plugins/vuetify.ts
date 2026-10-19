import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'

export const STORAGE_KEY = 'recetario-tema'

/** Tema guardado en el navegador; sin preferencia previa se sigue al sistema. */
function temaInicial(): 'light' | 'dark' | 'system' {
  try {
    const guardado = localStorage.getItem(STORAGE_KEY)
    if (guardado === 'light' || guardado === 'dark') return guardado
  } catch {
    // Sin acceso a localStorage (modo privado): se usa el del sistema
  }
  return 'system'
}

export default createVuetify({
  theme: {
    defaultTheme: temaInicial(),
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#D84315', // naranja tomate
          secondary: '#00695C', // verde hierbas
          background: '#FFF8F0', // crema suave
          surface: '#FFFFFF',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#FF8A65', // el naranja aclarado mantiene el contraste sobre fondo oscuro
          secondary: '#4DB6AC',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: 'lg' },
    VCard: { rounded: 'xl' },
  },
})
