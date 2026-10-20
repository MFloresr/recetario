import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { aApiError } from '@/api/client'
import { mealPlansApi } from '@/api/endpoints'
import type { MealPlan, OpcionesPlan } from '@/types/api'

export const useMealPlanStore = defineStore('mealPlan', () => {
  const planes = ref<MealPlan[]>([])
  const seleccionadoId = ref<number | null>(null)
  const cargando = ref(false)
  const cargado = ref(false)
  const generando = ref(false)

  const actual = computed(
    () => planes.value.find((p) => p.id === seleccionadoId.value) ?? planes.value[0] ?? null,
  )

  async function cargar(forzar = false) {
    if (cargado.value && !forzar) return
    cargando.value = true
    try {
      planes.value = await mealPlansApi.list()
      cargado.value = true
    } catch (e) {
      throw aApiError(e)
    } finally {
      cargando.value = false
    }
  }

  async function generar(opciones: OpcionesPlan) {
    generando.value = true
    try {
      const plan = await mealPlansApi.generate(opciones)
      planes.value = [plan, ...planes.value]
      seleccionadoId.value = plan.id
      return plan
    } catch (e) {
      throw aApiError(e)
    } finally {
      generando.value = false
    }
  }

  async function eliminar(id: number) {
    try {
      await mealPlansApi.remove(id)
      planes.value = planes.value.filter((p) => p.id !== id)
      if (seleccionadoId.value === id) seleccionadoId.value = null
    } catch (e) {
      throw aApiError(e)
    }
  }

  function vaciar() {
    planes.value = []
    seleccionadoId.value = null
    cargado.value = false
  }

  return {
    planes,
    seleccionadoId,
    actual,
    cargando,
    cargado,
    generando,
    cargar,
    generar,
    eliminar,
    vaciar,
  }
})
