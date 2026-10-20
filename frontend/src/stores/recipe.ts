import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { aApiError } from '@/api/client'
import { aiApi, favoritesApi, recipesApi } from '@/api/endpoints'
import type {
  AiAdaptation,
  AiSuggestion,
  Favorite,
  Recipe,
  RecipeSummary,
  SuggestionFilters,
} from '@/types/api'

export const useRecipeStore = defineStore('recipe', () => {
  const resultados = ref<RecipeSummary[]>([])
  const buscado = ref(false)
  const buscando = ref(false)
  const filtros = ref<SuggestionFilters>({ category: '', maxMissing: null, search: '' })

  const favoritos = ref<Favorite[]>([])
  const favoritosCargados = ref(false)
  const cargandoFavoritos = ref(false)

  const sugerenciasIa = ref<AiSuggestion[]>([])
  const cargandoIa = ref(false)

  const idsFavoritos = computed(() => new Set(favoritos.value.map((f) => f.recipe.external_id)))

  function esFavorito(externalId: string) {
    return idsFavoritos.value.has(externalId)
  }

  async function buscar(ingredientes: string[]) {
    buscando.value = true
    try {
      const respuesta = await recipesApi.suggestions(ingredientes, filtros.value)
      resultados.value = respuesta.results
      buscado.value = true
    } catch (e) {
      throw aApiError(e)
    } finally {
      buscando.value = false
    }
  }

  async function obtenerDetalle(externalId: string, ingredientes: string[]): Promise<Recipe> {
    try {
      return await recipesApi.detail(externalId, ingredientes)
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function cargarFavoritos(forzar = false) {
    if (favoritosCargados.value && !forzar) return
    cargandoFavoritos.value = true
    try {
      favoritos.value = await favoritesApi.list()
      favoritosCargados.value = true
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargandoFavoritos.value = false
    }
  }

  async function añadirFavorito(externalId: string) {
    try {
      const favorito = await favoritesApi.create(externalId)
      favoritos.value = [favorito, ...favoritos.value]
      return favorito
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function quitarFavorito(id: number) {
    try {
      await favoritesApi.remove(id)
      favoritos.value = favoritos.value.filter((f) => f.id !== id)
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function alternarFavorito(externalId: string) {
    const existente = favoritos.value.find((f) => f.recipe.external_id === externalId)
    if (existente) await quitarFavorito(existente.id)
    else await añadirFavorito(externalId)
    return !existente
  }

  /** Guarda en el recetario una receta de la IA (queda como favorita, con todos sus datos). */
  async function guardarRecetaIa(receta: AiSuggestion) {
    try {
      const favorito = await favoritesApi.createFromAi(receta)
      favoritos.value = [favorito, ...favoritos.value]
      return favorito
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function guardarNotas(id: number, notas: string) {
    try {
      const actualizado = await favoritesApi.updateNotes(id, notas)
      favoritos.value = favoritos.value.map((f) => (f.id === id ? actualizado : f))
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function pedirSugerenciasIa(ingredientes: string[], tipoComida = '', consulta = '') {
    cargandoIa.value = true
    sugerenciasIa.value = []
    try {
      sugerenciasIa.value = await aiApi.suggestions(ingredientes, tipoComida, consulta)
      favoritosCargados.value = false // el servidor guarda solas las recetas generadas: «Mis recetas» se recarga
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargandoIa.value = false
    }
  }

  async function adaptarReceta(receta: Recipe, disponibles: string[]): Promise<AiAdaptation> {
    try {
      return await aiApi.adaptRecipe(receta, disponibles)
    } catch (e) {
      throw aApiError(e)
    }
  }

  function vaciar() {
    resultados.value = []
    buscado.value = false
    favoritos.value = []
    favoritosCargados.value = false
    sugerenciasIa.value = []
  }

  return {
    resultados,
    buscado,
    buscando,
    filtros,
    favoritos,
    favoritosCargados,
    cargandoFavoritos,
    sugerenciasIa,
    cargandoIa,
    esFavorito,
    buscar,
    obtenerDetalle,
    cargarFavoritos,
    añadirFavorito,
    guardarRecetaIa,
    quitarFavorito,
    alternarFavorito,
    guardarNotas,
    pedirSugerenciasIa,
    adaptarReceta,
    vaciar,
  }
})
