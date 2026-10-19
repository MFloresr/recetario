import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { aApiError } from '@/api/client'
import { ingredientsApi } from '@/api/endpoints'
import type { Ingredient } from '@/types/api'

export const usePantryStore = defineStore('pantry', () => {
  const items = ref<Ingredient[]>([])
  const cargando = ref(false)
  const cargado = ref(false)

  /** Nombres de lo que hay en casa: lo que se envía al buscar recetas. */
  const nombresDisponibles = computed(() =>
    items.value.filter((i) => i.in_pantry).map((i) => i.name),
  )

  async function cargar(forzar = false) {
    if (cargado.value && !forzar) return
    cargando.value = true
    try {
      items.value = await ingredientsApi.list()
      cargado.value = true
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargando.value = false
    }
  }

  async function añadir(nombre: string, cantidad = '') {
    try {
      const creado = await ingredientsApi.create(nombre.trim(), cantidad)
      items.value = [...items.value, creado].sort((a, b) => a.name.localeCompare(b.name, 'es'))
      return creado
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function cambiarCantidad(id: number, cantidad: string) {
    try {
      const actualizado = await ingredientsApi.update(id, { quantity: cantidad })
      items.value = items.value.map((i) => (i.id === id ? actualizado : i))
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function eliminar(id: number) {
    try {
      await ingredientsApi.remove(id)
      items.value = items.value.filter((i) => i.id !== id)
    } catch (e) {
      throw aApiError(e)
    }
  }

  function vaciar() {
    items.value = []
    cargado.value = false
  }

  return {
    items,
    cargando,
    cargado,
    nombresDisponibles,
    cargar,
    añadir,
    cambiarCantidad,
    eliminar,
    vaciar,
  }
})
