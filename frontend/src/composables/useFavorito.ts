import { ref } from 'vue'
import { useRecipeStore } from '@/stores/recipe'
import { useUiStore } from '@/stores/ui'
import { notificarError } from '@/utils/errores'

/**
 * Añadir o quitar una receta de favoritos. Quitarla pide confirmación: la vista debe pintar un
 * ConfirmDialog con `confirmando`, `abrirConfirmacion` y `confirmarQuitar`.
 */
export function useFavorito() {
  const recipes = useRecipeStore()
  const ui = useUiStore()
  const confirmando = ref(false)
  const trabajando = ref(false)
  const pendiente = ref<string | null>(null)

  async function guardar(externalId: string) {
    trabajando.value = true
    try {
      await recipes.añadirFavorito(externalId)
      ui.mostrarAviso('Receta guardada en favoritos', 'success')
    } catch (e) {
      notificarError(e)
    } finally {
      trabajando.value = false
    }
  }

  function alternar(externalId: string) {
    if (recipes.esFavorito(externalId)) {
      pendiente.value = externalId
      confirmando.value = true
    } else {
      void guardar(externalId)
    }
  }

  async function confirmarQuitar() {
    const externalId = pendiente.value
    const favorito = recipes.favoritos.find((f) => f.recipe.external_id === externalId)
    if (!favorito) {
      confirmando.value = false
      return
    }
    trabajando.value = true
    try {
      await recipes.quitarFavorito(favorito.id)
      ui.mostrarAviso('Receta quitada de favoritos', 'success')
    } catch (e) {
      notificarError(e)
    } finally {
      trabajando.value = false
      confirmando.value = false
      pendiente.value = null
    }
  }

  return { confirmando, trabajando, alternar, confirmarQuitar }
}
