<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { dishesApi } from '@/api/endpoints'
import EmptyState from '@/components/EmptyState.vue'
import type { Plato } from '@/types/api'
import { mensajeDeError } from '@/utils/errores'

const POR_PAGINA = 24
const DIETAS = ['vegetariano', 'vegano', 'sin gluten', 'sin lactosa', 'pescetariano']
const COMIDAS = ['desayuno', 'almuerzo', 'cena', 'postre', 'entrante', 'plato principal', 'snack', 'bebida']

const nombresPais = new Intl.DisplayNames(['es'], { type: 'region' })
function nombreDePais(codigo: string): string {
  try {
    return nombresPais.of(codigo) ?? codigo
  } catch {
    return codigo
  }
}

const paises = ref<{ title: string; value: string }[]>([])
const pais = ref('')
const dieta = ref('')
const comida = ref('')
const texto = ref('')
const platos = ref<Plato[]>([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const detalle = ref<Plato | null>(null)

const hayMas = computed(() => platos.value.length < total.value)
const pasos = computed(() =>
  (detalle.value?.steps ?? '')
    .split('\n')
    .map((p) => p.trim())
    .filter(Boolean),
)

async function cargar(reiniciar: boolean) {
  cargando.value = true
  error.value = ''
  try {
    const { count, results } = await dishesApi.list({
      country: pais.value || undefined,
      diet: dieta.value || undefined,
      meal: comida.value || undefined,
      q: texto.value.trim() || undefined,
      limit: POR_PAGINA,
      offset: reiniciar ? 0 : platos.value.length,
    })
    total.value = count
    platos.value = reiniciar ? results : [...platos.value, ...results]
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}

let espera: ReturnType<typeof setTimeout> | undefined
watch([pais, dieta, comida], () => void cargar(true))
watch(texto, () => {
  clearTimeout(espera)
  espera = setTimeout(() => void cargar(true), 350)
})

onMounted(async () => {
  try {
    const lista = await dishesApi.countries()
    paises.value = lista.map((p) => ({
      title: `${nombreDePais(p.country)} (${p.total})`,
      value: p.country,
    }))
  } catch (e) {
    error.value = mensajeDeError(e)
  }
  await cargar(true)
})
</script>

<template>
  <v-container class="py-6" style="max-width: 1100px">
    <h1 class="text-h5 mb-1">Explorar platos del mundo</h1>
    <p class="text-medium-emphasis mb-4">
      Catálogo por país, tipo de comida y dieta. Las etiquetas de dieta son orientativas: si tienes
      alergias o intolerancias, comprueba siempre los ingredientes.
    </p>

    <v-row dense>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="texto"
          label="Buscar plato"
          prepend-inner-icon="mdi-magnify"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" sm="4" md="3">
        <v-autocomplete v-model="pais" :items="paises" label="País" clearable hide-details />
      </v-col>
      <v-col cols="6" sm="4" md="3">
        <v-select v-model="comida" :items="COMIDAS" label="Tipo de comida" clearable hide-details />
      </v-col>
      <v-col cols="6" sm="4" md="3">
        <v-select v-model="dieta" :items="DIETAS" label="Dieta" clearable hide-details />
      </v-col>
    </v-row>

    <v-alert v-if="error" type="error" class="mt-4" role="alert">{{ error }}</v-alert>

    <EmptyState
      v-else-if="!cargando && !platos.length"
      icono="mdi-earth-off"
      titulo="No hay platos con esos filtros"
      texto="Prueba con otro país o quita algún filtro."
    />

    <template v-else>
      <p class="text-caption text-medium-emphasis mt-4" aria-live="polite">{{ total }} platos</p>
      <v-row class="mt-1">
        <v-col v-for="p in platos" :key="p.id" cols="12" sm="6" md="4" lg="3">
          <v-card class="h-100" hover @click="detalle = p">
            <v-img :src="p.image" :alt="p.name_es" height="150" cover>
              <template #placeholder>
                <div class="d-flex align-center justify-center fill-height">
                  <v-icon icon="mdi-silverware-fork-knife" size="36" />
                </div>
              </template>
            </v-img>
            <v-card-item>
              <v-card-title class="text-wrap text-subtitle-1">{{ p.name_es }}</v-card-title>
              <v-card-subtitle v-if="p.country">{{ nombreDePais(p.country) }}</v-card-subtitle>
            </v-card-item>
            <v-card-text v-if="p.diets.length || p.calories" class="pt-0">
              <v-chip v-for="d in p.diets" :key="d" size="x-small" class="mr-1 mb-1" variant="tonal">{{
                d
              }}</v-chip>
              <span v-if="p.calories" class="text-caption">{{ p.calories }} kcal</span>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <div v-if="hayMas" class="text-center mt-4">
        <v-btn :loading="cargando" variant="tonal" @click="cargar(false)">Ver más platos</v-btn>
      </div>
    </template>

    <v-dialog
      :model-value="!!detalle"
      max-width="640"
      scrollable
      @update:model-value="detalle = null"
    >
      <v-card v-if="detalle">
        <v-img v-if="detalle.image" :src="detalle.image" :alt="detalle.name_es" height="220" cover />
        <v-card-title class="text-wrap">{{ detalle.name_es }}</v-card-title>
        <v-card-subtitle v-if="detalle.country">{{
          nombreDePais(detalle.country)
        }}</v-card-subtitle>
        <v-card-text>
          <p v-if="detalle.description" class="mb-3">{{ detalle.description }}</p>
          <div v-if="detalle.diets.length" class="mb-3">
            <v-chip v-for="d in detalle.diets" :key="d" size="small" class="mr-1" variant="tonal">{{
              d
            }}</v-chip>
            <v-alert
              v-if="!detalle.reviewed"
              type="warning"
              density="compact"
              variant="tonal"
              class="mt-2"
            >
              Etiquetas generadas por IA y sin revisar: verifica los ingredientes si tienes
              alergias.
            </v-alert>
          </div>
          <template v-if="detalle.ingredients.length">
            <h2 class="text-subtitle-1 mb-1">Ingredientes</h2>
            <ul class="mb-3 ml-4">
              <li v-for="(i, n) in detalle.ingredients" :key="n">
                {{ [i.measure, i.ingredient].filter(Boolean).join(' ') }}
              </li>
            </ul>
          </template>
          <template v-if="pasos.length">
            <h2 class="text-subtitle-1 mb-1">Preparación</h2>
            <ol class="ml-4">
              <li v-for="(p, n) in pasos" :key="n" class="mb-1">{{ p }}</li>
            </ol>
          </template>
          <p v-else-if="!detalle.ingredients.length" class="text-medium-emphasis">
            Este plato aún no tiene receta en el catálogo.
          </p>
          <p v-if="detalle.image_credit" class="text-caption text-medium-emphasis mt-4">
            Foto: {{ detalle.image_credit
            }}<span v-if="detalle.image_license"> · {{ detalle.image_license }}</span>
          </p>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn @click="detalle = null">Cerrar</v-btn></v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
