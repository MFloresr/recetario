import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { aApiError } from '@/api/client'
import { shoppingApi } from '@/api/endpoints'
import type { MissingIngredient, ShoppingItem } from '@/types/api'

export const useShoppingListStore = defineStore('shoppingList', () => {
  const items = ref<ShoppingItem[]>([])
  const cargando = ref(false)
  const cargado = ref(false)

  const pendientes = computed(() => items.value.filter((i) => !i.bought).length)
  const comprados = computed(() => items.value.filter((i) => i.bought).length)

  async function cargar(forzar = false) {
    if (cargado.value && !forzar) return
    cargando.value = true
    try {
      items.value = await shoppingApi.list()
      cargado.value = true
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargando.value = false
    }
  }

  async function añadir(nombre: string, cantidad = '') {
    try {
      const item = await shoppingApi.create(nombre.trim(), cantidad)
      const existe = items.value.some((i) => i.id === item.id)
      items.value = existe
        ? items.value.map((i) => (i.id === item.id ? item : i))
        : [...items.value, item]
      return item
    } catch (e) {
      throw aApiError(e)
    }
  }

  /** Añade a la lista los ingredientes que faltan de una receta (en español si se conoce el nombre). */
  async function añadirFaltantes(faltantes: MissingIngredient[]) {
    for (const f of faltantes) await añadir(f.name_es ?? f.ingredient, f.measure)
    return faltantes.length
  }

  async function marcar(id: number, comprado: boolean) {
    const antes = items.value
    items.value = items.value.map((i) => (i.id === id ? { ...i, bought: comprado } : i)) // respuesta inmediata
    try {
      await shoppingApi.update(id, { bought: comprado })
    } catch (e) {
      items.value = antes
      throw aApiError(e)
    }
  }

  async function eliminar(id: number) {
    try {
      await shoppingApi.remove(id)
      items.value = items.value.filter((i) => i.id !== id)
    } catch (e) {
      throw aApiError(e)
    }
  }

  async function limpiarComprados() {
    try {
      const { deleted } = await shoppingApi.clearBought()
      items.value = items.value.filter((i) => !i.bought)
      return deleted
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
    pendientes,
    comprados,
    cargar,
    añadir,
    añadirFaltantes,
    marcar,
    eliminar,
    limpiarComprados,
    vaciar,
  }
})
