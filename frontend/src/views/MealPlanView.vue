<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { aiApi } from '@/api/endpoints'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useMealPlanStore } from '@/stores/mealPlan'
import { usePantryStore } from '@/stores/pantry'
import { useRecipeStore } from '@/stores/recipe'
import { useUiStore } from '@/stores/ui'
import type { ComidaPlan, DiaPlan } from '@/types/api'
import { tipoComida } from '@/utils/catalogo'
import { mensajeDeError, notificarError } from '@/utils/errores'

const plan = useMealPlanStore()
const pantry = usePantryStore()
const recipes = useRecipeStore()
const ui = useUiStore()
const router = useRouter()

const OBJETIVOS = ['mantener el peso', 'bajar de peso', 'ganar músculo', 'comer más sano']
const COMIDAS = [
  { valor: 'desayuno', etiqueta: 'Desayuno' },
  { valor: 'almuerzo', etiqueta: 'Almuerzo' },
  { valor: 'merienda', etiqueta: 'Merienda' },
  { valor: 'cena', etiqueta: 'Cena' },
]
const DIETAS = [
  { title: 'Sin restricciones', value: '' },
  { title: 'Mediterránea', value: 'mediterránea' },
  { title: 'Vegetariana', value: 'vegetariana' },
  { title: 'Vegana', value: 'vegana' },
  { title: 'Sin gluten', value: 'sin gluten' },
  { title: 'Sin lactosa', value: 'sin lactosa' },
  { title: 'Baja en carbohidratos', value: 'baja en carbohidratos' },
]

const objetivo = ref('mantener el peso')
const comidas = ref(['desayuno', 'almuerzo', 'merienda', 'cena'])
const calorias = ref('')
const dieta = ref('')
const evitar = ref<string[]>([])
const usarDespensa = ref(false)
const error = ref('')
const abrirFormulario = ref<number[]>([0])
const abriendo = ref<string | null>(null)
const confirmandoBorrar = ref(false)
const borrando = ref(false)
// Receta ya creada para cada plato de esta pantalla: la segunda vez se abre sin pedirla otra vez a la IA
const recetaDePlato = ref<Record<string, string>>({})

const hoy = (new Date().getDay() + 6) % 7 // lunes = 0
const hayCalorias = computed(() => {
  const n = Number(calorias.value)
  return calorias.value !== '' && (!Number.isInteger(n) || n < 1000 || n > 5000)
})

onMounted(async () => {
  try {
    await plan.cargar()
    if (plan.actual) abrirFormulario.value = []
  } catch (e) {
    notificarError(e)
  }
})

async function generar() {
  error.value = ''
  try {
    if (usarDespensa.value) await pantry.cargar()
    await plan.generar({
      goal: objetivo.value,
      meals: comidas.value,
      calories: calorias.value === '' ? null : Number(calorias.value),
      diet: dieta.value,
      avoid: evitar.value,
      use_pantry: usarDespensa.value,
    })
    abrirFormulario.value = []
    ui.mostrarAviso('Tu dieta de la semana está lista y guardada', 'success')
  } catch (e) {
    error.value = mensajeDeError(e)
  }
}

const COLORES_DIA = ['#2e7d6b', '#3b6fb6', '#8a5fb8', '#c26a3d', '#b8478a', '#4f8f3a', '#c2923a']

function totalDia(dia: DiaPlan): number {
  return dia.meals.reduce((suma, m) => suma + (m.calories ?? 0), 0)
}

function iconoComida(tipo: string): string {
  return tipoComida(tipo)?.icono ?? 'mdi-food'
}
function etiquetaComida(tipo: string): string {
  return tipoComida(tipo)?.etiqueta ?? tipo
}

async function verReceta(comida: ComidaPlan) {
  const conocida = recetaDePlato.value[comida.title]
  if (conocida) {
    await router.push({ name: 'recipe', params: { externalId: conocida } })
    return
  }
  abriendo.value = comida.title
  try {
    const [receta] = await aiApi.suggestions(comida.ingredients, '', comida.title, 1)
    if (!receta?.external_id) {
      ui.mostrarAviso('La IA no pudo detallar esta receta. Inténtalo de nuevo.', 'error')
      return
    }
    recetaDePlato.value[comida.title] = receta.external_id
    recipes.favoritosCargados = false // la receta nueva ya está en «Mis recetas»
    await router.push({ name: 'recipe', params: { externalId: receta.external_id } })
  } catch (e) {
    notificarError(e)
  } finally {
    abriendo.value = null
  }
}

async function borrarPlan() {
  const actual = plan.actual
  if (!actual) return
  borrando.value = true
  try {
    await plan.eliminar(actual.id)
    confirmandoBorrar.value = false
    ui.mostrarAviso('Dieta eliminada', 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    borrando.value = false
  }
}

function imprimir() {
  window.print()
}

function fecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
}
</script>

<template>
  <v-container class="plan-view py-6" style="max-width: 1280px">
    <div class="d-flex align-center flex-wrap ga-2 mb-1 no-imprimir">
      <h1 class="text-h4 font-weight-bold">Dieta semanal</h1>
      <v-spacer />
      <v-btn
        v-if="plan.actual"
        variant="tonal"
        prepend-icon="mdi-printer-outline"
        @click="imprimir"
      >
        Imprimir
      </v-btn>
    </div>
    <p class="text-medium-emphasis mb-5 no-imprimir">
      Pide a la IA un menú de lunes a domingo. Se guarda para que lo consultes cuando quieras.
    </p>

    <v-expansion-panels v-model="abrirFormulario" class="mb-6 no-imprimir" variant="accordion">
      <v-expansion-panel :value="0" :title="plan.actual ? 'Crear otra dieta' : 'Crea tu dieta'">
        <template #text>
          <form class="form-plan" @submit.prevent="generar">
            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="objetivo"
                  :items="OBJETIVOS"
                  label="Objetivo"
                  variant="outlined"
                  hide-details
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="dieta"
                  :items="DIETAS"
                  label="Tipo de dieta"
                  variant="outlined"
                  hide-details
                />
              </v-col>
              <v-col cols="12">
                <p class="text-body-2 mb-1">Comidas de cada día</p>
                <v-chip-group v-model="comidas" multiple column selected-class="text-primary">
                  <v-chip
                    v-for="c in COMIDAS"
                    :key="c.valor"
                    :value="c.valor"
                    filter
                    variant="outlined"
                    >{{ c.etiqueta }}</v-chip
                  >
                </v-chip-group>
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="calorias"
                  label="Calorías al día (opcional)"
                  placeholder="Ej.: 2000"
                  inputmode="numeric"
                  variant="outlined"
                  :error="hayCalorias"
                  :hint="hayCalorias ? 'Entre 1000 y 5000' : ''"
                  :persistent-hint="hayCalorias"
                />
              </v-col>
              <v-col cols="12" md="8">
                <v-combobox
                  v-model="evitar"
                  label="Alimentos que quieres evitar (opcional)"
                  placeholder="Escribe y pulsa Enter: marisco, frutos secos…"
                  multiple
                  chips
                  closable-chips
                  variant="outlined"
                  hide-details
                />
              </v-col>
              <v-col cols="12">
                <v-switch
                  v-model="usarDespensa"
                  color="primary"
                  label="Aprovechar lo que tengo en la despensa"
                  hide-details
                  density="comfortable"
                />
              </v-col>
            </v-row>
            <v-btn
              type="submit"
              color="primary"
              size="x-large"
              prepend-icon="mdi-creation"
              class="mt-3"
              :loading="plan.generando"
              :disabled="comidas.length < 2 || hayCalorias"
            >
              Generar mi dieta de la semana
            </v-btn>
            <p v-if="comidas.length < 2" class="text-caption text-error mt-2">
              Elige al menos dos comidas al día.
            </p>
          </form>
        </template>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-alert v-if="error" type="warning" variant="tonal" class="mb-5 no-imprimir">{{
      error
    }}</v-alert>

    <div v-if="plan.generando" aria-live="polite">
      <p class="text-medium-emphasis mb-3">
        La IA está preparando tu semana… puede tardar hasta un minuto.
      </p>
      <v-row>
        <v-col v-for="n in 4" :key="n" cols="12" sm="6" md="4" lg="3">
          <v-skeleton-loader
            type="heading, list-item-three-line, list-item-three-line, list-item-three-line"
          />
        </v-col>
      </v-row>
    </div>

    <template v-else-if="plan.actual">
      <div class="d-flex align-center flex-wrap ga-3 mb-3">
        <div>
          <h2 class="text-h5 font-weight-bold">{{ plan.actual.title }}</h2>
          <p class="text-body-2 text-medium-emphasis mb-0">
            {{ plan.actual.options.goal }}
            <template v-if="plan.actual.options.diet"> · {{ plan.actual.options.diet }}</template>
            <template v-if="plan.actual.options.calories">
              · ~{{ plan.actual.options.calories }} kcal/día</template
            >
          </p>
        </div>
        <v-spacer />
        <v-select
          v-if="plan.planes.length > 1"
          :model-value="plan.actual?.id"
          :items="
            plan.planes.map((p) => ({ title: `${p.title} · ${fecha(p.created_at)}`, value: p.id }))
          "
          label="Dietas guardadas"
          variant="outlined"
          density="compact"
          hide-details
          class="selector-plan no-imprimir"
          style="max-width: 320px"
          @update:model-value="(id: number) => (plan.seleccionadoId = id)"
        />
        <v-btn
          variant="text"
          color="error"
          prepend-icon="mdi-delete-outline"
          class="no-imprimir"
          @click="confirmandoBorrar = true"
        >
          Eliminar
        </v-btn>
      </div>

      <v-alert
        v-if="plan.actual.notes"
        type="info"
        variant="tonal"
        density="comfortable"
        icon="mdi-lightbulb-on-outline"
        class="mb-4"
      >
        {{ plan.actual.notes }}
      </v-alert>

      <v-row class="dias">
        <v-col v-for="(dia, i) in plan.actual.days" :key="dia.day" cols="12" sm="6" md="4" lg="3">
          <v-card class="dia h-100" :class="{ 'dia-hoy': i === hoy }" variant="flat" border>
            <div class="dia-cabecera" :style="{ background: COLORES_DIA[i % COLORES_DIA.length] }">
              <span class="text-h6 font-weight-bold">{{ dia.day }}</span>
              <v-chip v-if="i === hoy" size="x-small" color="white" variant="flat" class="ml-2"
                >Hoy</v-chip
              >
              <v-spacer />
              <span v-if="totalDia(dia)" class="text-body-2">{{ totalDia(dia) }} kcal</span>
            </div>
            <div class="pa-3 d-flex flex-column ga-3">
              <div v-for="(c, j) in dia.meals" :key="j" class="comida" :class="`comida-${c.type}`">
                <div class="d-flex align-center text-caption text-medium-emphasis mb-1">
                  <v-icon :icon="iconoComida(c.type)" size="16" class="mr-1" aria-hidden="true" />
                  {{ etiquetaComida(c.type) }}
                  <v-spacer />
                  <span v-if="c.calories">{{ c.calories }} kcal</span>
                </div>
                <p class="font-weight-bold mb-1 titulo-comida">{{ c.title }}</p>
                <p v-if="c.description" class="text-body-2 text-medium-emphasis mb-2">
                  {{ c.description }}
                </p>
                <div v-if="c.ingredients.length" class="d-flex flex-wrap ga-1 mb-2">
                  <v-chip v-for="ing in c.ingredients.slice(0, 5)" :key="ing" size="x-small">{{
                    ing
                  }}</v-chip>
                </div>
                <v-btn
                  size="small"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-chef-hat"
                  class="no-imprimir"
                  :loading="abriendo === c.title"
                  :disabled="Boolean(abriendo)"
                  @click="verReceta(c)"
                >
                  Ver receta
                </v-btn>
              </div>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <p class="text-caption text-medium-emphasis mt-4">
        Menú orientativo generado por una IA: las calorías son aproximadas y no sustituyen el
        consejo de un nutricionista.
      </p>
    </template>

    <EmptyState
      v-else-if="plan.cargado && !error"
      icono="mdi-calendar-week"
      titulo="Todavía no tienes ninguna dieta"
      texto="Elige tu objetivo arriba y la IA te prepara el menú de toda la semana."
    />

    <ConfirmDialog
      v-model="confirmandoBorrar"
      titulo="¿Eliminar esta dieta?"
      texto="Se borra el menú de la semana. Las recetas que hayas abierto desde él siguen en Mis recetas."
      :cargando="borrando"
      @confirmar="borrarPlan"
    />
  </v-container>
</template>

<style scoped>
.dia {
  overflow: hidden;
  border-radius: 16px;
}
.dia-hoy {
  outline: 3px solid rgb(var(--v-theme-primary));
}
.dia-cabecera {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  color: #fff;
}
.comida {
  padding: 8px 10px 10px 12px;
  border-left: 4px solid rgb(var(--v-theme-primary));
  border-radius: 4px 12px 12px 4px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.comida-desayuno {
  border-left-color: #e0a526;
}
.comida-almuerzo {
  border-left-color: #2e9e6b;
}
.comida-merienda {
  border-left-color: #9a62c8;
}
.comida-cena {
  border-left-color: #4a6fd0;
}
.comida-snack {
  border-left-color: #c26a3d;
}
.titulo-comida {
  line-height: 1.25;
}
</style>

<style>
@media print {
  .v-app-bar,
  .v-navigation-drawer,
  .v-bottom-navigation,
  .no-imprimir {
    display: none !important;
  }
  .v-main {
    padding: 0 !important;
  }
}
</style>
