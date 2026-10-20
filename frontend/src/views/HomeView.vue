<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AiSuggestionsDialog from '@/components/AiSuggestionsDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import IngredientAdder from '@/components/IngredientAdder.vue'
import IngredientChip from '@/components/IngredientChip.vue'
import RecipeCard from '@/components/RecipeCard.vue'
import { useFavorito } from '@/composables/useFavorito'
import { usePantryStore } from '@/stores/pantry'
import { useRecipeStore } from '@/stores/recipe'
import { useShoppingListStore } from '@/stores/shoppingList'
import { useUiStore } from '@/stores/ui'
import type { AiSuggestion, Ingredient } from '@/types/api'
import { CATEGORIAS_RECETA } from '@/utils/catalogo'
import { mensajeDeError, notificarError } from '@/utils/errores'

const router = useRouter()
const pantry = usePantryStore()
const recipes = useRecipeStore()
const ui = useUiStore()
const {
  confirmando: confirmandoFavorito,
  trabajando: trabajandoFavorito,
  alternar: alternarFavorito,
  confirmarQuitar: confirmarQuitarFavorito,
} = useFavorito()

const añadiendo = ref(false)
const porEliminar = ref<Ingredient | null>(null)
const confirmandoEliminar = ref(false)
const eliminando = ref(false)

const iaAbierta = ref(false)
const iaError = ref('')
const iaTipo = ref('')
const iaConsulta = ref('')
const guardandoIa = ref<string | null>(null)
const shopping = useShoppingListStore()

const disponibles = computed(() => pantry.items.filter((i) => i.in_pantry))
const opcionesCategoria = [
  { title: 'Todas', value: '' },
  ...CATEGORIAS_RECETA.map((c) => ({ title: c.etiqueta, value: c.valor })),
]
const opcionesFaltantes = [
  { title: 'Sin límite', value: null },
  { title: 'Ninguno', value: 0 },
  { title: 'Hasta 1', value: 1 },
  { title: 'Hasta 2', value: 2 },
  { title: 'Hasta 3', value: 3 },
  { title: 'Hasta 5', value: 5 },
]

onMounted(async () => {
  try {
    await Promise.all([pantry.cargar(), recipes.cargarFavoritos()])
  } catch (e) {
    notificarError(e)
  }
})

async function añadir(nombre: string) {
  añadiendo.value = true
  try {
    await pantry.añadir(nombre)
    ui.mostrarAviso(`${nombre} añadido a tu despensa`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    añadiendo.value = false
  }
}

function pedirEliminar(item: Ingredient) {
  porEliminar.value = item
  confirmandoEliminar.value = true
}

async function eliminar() {
  if (!porEliminar.value) return
  eliminando.value = true
  try {
    await pantry.eliminar(porEliminar.value.id)
    ui.mostrarAviso(`${porEliminar.value.name} eliminado`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    eliminando.value = false
    confirmandoEliminar.value = false
    porEliminar.value = null
  }
}

async function buscar() {
  if (!pantry.nombresDisponibles.length) return
  try {
    await recipes.buscar(pantry.nombresDisponibles)
  } catch (e) {
    notificarError(e)
  }
}

async function sugerirConIa() {
  iaAbierta.value = true
  iaError.value = ''
  const consulta = iaConsulta.value.trim()
  if (!consulta && !pantry.nombresDisponibles.length) {
    recipes.sugerenciasIa = [] // sin ingredientes ni búsqueda no hay nada que pedir: el diálogo invita a escribir
    return
  }
  try {
    await recipes.pedirSugerenciasIa(pantry.nombresDisponibles, iaTipo.value, consulta)
  } catch (e) {
    iaError.value = mensajeDeError(e)
  }
}

const recetasIaGuardadas = computed(() =>
  recipes.favoritos.filter((f) => f.recipe.source === 'ai').map((f) => f.recipe.title),
)

async function guardarRecetaIa(receta: AiSuggestion) {
  guardandoIa.value = receta.title
  try {
    await recipes.guardarRecetaIa(receta)
    ui.mostrarAviso('Receta guardada en tu recetario', 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    guardandoIa.value = null
  }
}

function abrirRecetaIa(receta: AiSuggestion) {
  if (!receta.external_id) return
  iaAbierta.value = false
  void router.push({ name: 'recipe', params: { externalId: receta.external_id } })
}

async function añadirFaltantesIa(receta: AiSuggestion) {
  try {
    for (const nombre of receta.missing_ingredients) await shopping.añadir(nombre)
    ui.mostrarAviso(
      `${receta.missing_ingredients.length} ingredientes en tu lista de la compra`,
      'success',
    )
  } catch (e) {
    notificarError(e)
  }
}

watch(iaTipo, () => {
  if (iaAbierta.value) void sugerirConIa()
})
</script>

<template>
  <v-container class="home-view py-6" style="max-width: 1100px">
    <h1 class="text-h4 font-weight-bold mb-1">¿Qué cocino hoy?</h1>
    <p class="text-medium-emphasis mb-5">
      Añade lo que tienes en casa y te digo qué puedes preparar.
    </p>

    <v-card class="pa-4 mb-5" variant="flat" border>
      <IngredientAdder
        :cargando="añadiendo"
        :existentes="pantry.items.map((i) => i.name)"
        @añadir="añadir"
      />

      <div class="mt-4" aria-live="polite">
        <div v-if="pantry.cargando && !pantry.cargado" class="d-flex ga-2">
          <v-skeleton-loader v-for="n in 4" :key="n" type="chip" />
        </div>
        <div v-else-if="disponibles.length" class="d-flex flex-wrap ga-2">
          <IngredientChip
            v-for="i in disponibles"
            :key="i.id"
            :nombre="i.name"
            :cantidad="i.quantity"
            @quitar="pedirEliminar(i)"
          />
        </div>
        <p v-else class="text-medium-emphasis">Todavía no has añadido ingredientes.</p>
      </div>

      <div class="d-flex flex-column flex-sm-row ga-3 mt-5">
        <v-btn
          color="primary"
          size="x-large"
          prepend-icon="mdi-magnify"
          class="flex-grow-1"
          :loading="recipes.buscando"
          :disabled="!disponibles.length"
          @click="buscar"
        >
          Buscar recetas
        </v-btn>
        <v-btn
          color="secondary"
          variant="tonal"
          size="x-large"
          prepend-icon="mdi-creation"
          class="flex-grow-1"
          @click="sugerirConIa"
        >
          Sugiéreme algo con IA
        </v-btn>
      </div>

      <v-expansion-panels class="mt-4" variant="accordion" flat>
        <v-expansion-panel title="Filtros">
          <template #text>
            <v-row>
              <v-col cols="12" sm="4">
                <v-select
                  v-model="recipes.filtros.category"
                  :items="opcionesCategoria"
                  label="Categoría"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                >
                </v-select>
              </v-col>
              <v-col cols="12" sm="4">
                <v-select
                  v-model="recipes.filtros.maxMissing"
                  :items="opcionesFaltantes"
                  label="Ingredientes que faltan"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field
                  v-model="recipes.filtros.search"
                  label="Buscar por nombre"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                  clearable
                />
              </v-col>
            </v-row>
          </template>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card>

    <section aria-live="polite" aria-label="Resultados">
      <v-row v-if="recipes.buscando">
        <v-col v-for="n in 6" :key="n" cols="12" sm="6" md="4"
          ><v-skeleton-loader type="card"
        /></v-col>
      </v-row>
      <v-row v-else-if="recipes.resultados.length">
        <v-col v-for="r in recipes.resultados" :key="r.external_id" cols="12" sm="6" md="4">
          <RecipeCard
            :receta="r"
            :favorita="recipes.esFavorito(r.external_id)"
            :guardando="trabajandoFavorito"
            @alternar-favorito="alternarFavorito(r.external_id)"
          />
        </v-col>
      </v-row>
      <EmptyState
        v-else-if="recipes.buscado"
        icono="mdi-pot-steam-outline"
        titulo="No he encontrado recetas"
        texto="Prueba a añadir más ingredientes, a quitar filtros o a pedir ideas a la IA."
      />
      <EmptyState
        v-else
        icono="mdi-chef-hat"
        titulo="Añade ingredientes para descubrir qué puedes cocinar"
        texto="Escribe lo que tienes y pulsa «Buscar recetas»."
      />
    </section>

    <ConfirmDialog
      v-model="confirmandoEliminar"
      titulo="¿Quitar este ingrediente?"
      :texto="`Se eliminará «${porEliminar?.name ?? ''}» de tu despensa.`"
      :cargando="eliminando"
      @confirmar="eliminar"
    />
    <ConfirmDialog
      v-model="confirmandoFavorito"
      titulo="¿Quitar de favoritos?"
      texto="La receta dejará de aparecer en tus favoritos, junto con tus notas."
      confirmar="Quitar"
      :cargando="trabajandoFavorito"
      @confirmar="confirmarQuitarFavorito"
    />
    <AiSuggestionsDialog
      v-model="iaAbierta"
      v-model:tipo="iaTipo"
      v-model:consulta="iaConsulta"
      :guardadas="recetasIaGuardadas"
      :guardando="guardandoIa"
      :sugerencias="recipes.sugerenciasIa"
      :cargando="recipes.cargandoIa"
      :error="iaError"
      @buscar="sugerirConIa"
      @guardar="guardarRecetaIa"
      @añadir-faltantes="añadirFaltantesIa"
      @abrir="abrirRecetaIa"
      @reintentar="sugerirConIa"
    />
  </v-container>
</template>
