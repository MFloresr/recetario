import { defineStore } from 'pinia'
import { ref } from 'vue'
import { STORAGE_KEY } from '@/plugins/vuetify'

export type TemaElegido = 'light' | 'dark'
export type ColorAviso = 'success' | 'error' | 'info'

/** Estado de interfaz: tema, avisos (snackbar) y contador de peticiones en curso. */
export const useUiStore = defineStore('ui', () => {
  const tema = ref<TemaElegido | null>(null) // null = el del sistema
  const aviso = ref({ visible: false, texto: '', color: 'info' as ColorAviso })
  const peticiones = ref(0)

  function elegirTema(nuevo: TemaElegido) {
    tema.value = nuevo
    try {
      localStorage.setItem(STORAGE_KEY, nuevo)
    } catch {
      // Sin localStorage: el tema solo dura la sesión
    }
  }

  function mostrarAviso(texto: string, color: ColorAviso = 'info') {
    aviso.value = { visible: true, texto, color }
  }

  function empezarPeticion() {
    peticiones.value++
  }

  function terminarPeticion() {
    peticiones.value = Math.max(0, peticiones.value - 1)
  }

  return { tema, aviso, peticiones, elegirTema, mostrarAviso, empezarPeticion, terminarPeticion }
})
