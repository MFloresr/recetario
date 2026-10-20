<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AdaptRecipeDialog from '@/components/AdaptRecipeDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useFavorito } from '@/composables/useFavorito'
import { usePantryStore } from '@/stores/pantry'
import { useRecipeStore } from '@/stores/recipe'
import { useShoppingListStore } from '@/stores/shoppingList'
import { useUiStore } from '@/stores/ui'
import type { AiAdaptation, Recipe } from '@/types/api'
import { tipoComida } from '@/utils/catalogo'
import { mensajeDeError, notificarError } from '@/utils/errores'
import { normalizar, pasosDeInstrucciones } from '@/utils/texto'

const route = useRoute()
const pantry = usePantryStore()
const recipes = useRecipeStore()
const shopping = useShoppingListStore()
const ui = useUiStore()
const {
  confirmando: confirmandoFavorito,
  trabajando: trabajandoFavorito,
  alternar: alternarFavorito,
  confirmarQuitar: confirmarQuitarFavorito,
} = useFavorito()

const receta = ref<Recipe | null>(null)
const cargando = ref(true)
const error = ref('')
const añadiendoFaltantes = ref(false)

const adaptarAbierto = ref(false)
const adaptando = ref(false)
const adaptacion = ref<AiAdaptation | null>(null)
const adaptacionError = ref('')

const externalId = computed(() => String(route.params.externalId))
const esFavorita = computed(() =>
  receta.value ? recipes.esFavorito(receta.value.external_id) : false,
)
const tipo = computed(() => tipoComida(receta.value?.meal_type))
const esIa = computed(() => receta.value?.source === 'ai')
const pasos = computed(() => pasosDeInstrucciones(receta.value?.instructions ?? ''))
const faltantes = computed(() => receta.value?.match?.missing ?? [])
const faltanSet = computed(
  () => new Set((receta.value?.match?.missing_ingredients ?? []).map(normalizar)),
)
const puntuacion = computed(() => receta.value?.match?.match_score ?? null)
const colorPuntuacion = computed(() =>
  (puntuacion.value ?? 0) >= 75 ? 'secondary' : (puntuacion.value ?? 0) >= 40 ? 'warning' : 'error',
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    await Promise.all([pantry.cargar(), recipes.cargarFavoritos()])
    receta.value = await recipes.obtenerDetalle(externalId.value, pantry.nombresDisponibles)
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
watch(externalId, cargar)

async function añadirFaltantes() {
  if (!faltantes.value.length) return
  añadiendoFaltantes.value = true
  try {
    const n = await shopping.añadirFaltantes(faltantes.value)
    ui.mostrarAviso(`${n} ingrediente${n === 1 ? '' : 's'} en tu lista de la compra`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    añadiendoFaltantes.value = false
  }
}

async function adaptar() {
  if (!receta.value) return
  adaptarAbierto.value = true
  adaptando.value = true
  adaptacion.value = null
  adaptacionError.value = ''
  try {
    adaptacion.value = await recipes.adaptarReceta(receta.value, pantry.nombresDisponibles)
  } catch (e) {
    adaptacionError.value = mensajeDeError(e)
  } finally {
    adaptando.value = false
  }
}
</script>

<template>
  <v-container class="recipe-detail py-4" style="max-width: 900px">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'home' }" class="mb-2"
      >Volver</v-btn
    >

    <div v-if="cargando">
      <v-skeleton-loader type="image, heading, paragraph" />
    </div>

    <div v-else-if="error">
      <v-alert type="error" variant="tonal" class="mb-4" role="alert">{{ error }}</v-alert>
      <v-btn variant="tonal" prepend-icon="mdi-refresh" @click="cargar">Reintentar</v-btn>
    </div>

    <EmptyState
      v-else-if="!receta"
      icono="mdi-book-off-outline"
      titulo="No se encontró la receta"
    />

    <article v-else>
      <v-img
        v-if="receta.image"
        :src="receta.image"
        :alt="receta.title"
        height="280"
        cover
        rounded="xl"
        class="mb-4 foto-receta"
      />
      <p v-if="receta.image_page && receta.image" class="text-caption text-medium-emphasis mb-4">
        Foto orientativa:
        <a :href="receta.image_page" target="_blank" rel="noopener">{{ receta.image_credit }}</a>
      </p>

      <h1 class="text-h4 font-weight-bold mb-2">{{ receta.title }}</h1>
      <div class="d-flex flex-wrap ga-2 mb-4">
        <v-chip v-if="tipo" :prepend-icon="tipo.icono" color="secondary" variant="tonal">{{
          tipo.etiqueta
        }}</v-chip>
        <v-chip v-if="receta.category" prepend-icon="mdi-tag-outline">{{ receta.category }}</v-chip>
        <v-chip v-if="receta.area" prepend-icon="mdi-earth">{{ receta.area }}</v-chip>
        <template v-if="esIa">
          <v-chip v-if="receta.estimated_minutes" prepend-icon="mdi-clock-outline"
            >{{ receta.estimated_minutes }} min</v-chip
          >
          <v-chip v-if="receta.difficulty" prepend-icon="mdi-chef-hat"
            >Dificultad {{ receta.difficulty }}</v-chip
          >
          <v-chip v-if="receta.servings" prepend-icon="mdi-account-multiple-outline"
            >{{ receta.servings }} {{ receta.servings === 1 ? 'ración' : 'raciones' }}</v-chip
          >
          <v-chip prepend-icon="mdi-creation">Receta generada por IA</v-chip>
        </template>
        <v-chip v-else prepend-icon="mdi-database-outline">Fuente: TheMealDB</v-chip>
        <v-chip v-if="receta.translation?.provider" prepend-icon="mdi-translate">
          Traducción automática
        </v-chip>
      </div>

      <p v-if="esIa && receta.description" class="text-body-1 mb-4">{{ receta.description }}</p>

      <v-alert
        v-if="receta.translation && !receta.translation.complete"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        Parte de la receta sigue en inglés porque el traductor no estaba disponible. Vuelve a
        abrirla más tarde para verla completa.
      </v-alert>

      <v-card v-if="puntuacion !== null" class="pa-4 mb-4" variant="flat" border>
        <div class="d-flex align-center ga-3">
          <v-progress-linear
            :model-value="puntuacion"
            :color="colorPuntuacion"
            height="12"
            rounded
            aria-hidden="true"
          />
          <strong class="text-no-wrap">{{ puntuacion }}%</strong>
        </div>
        <p class="text-body-2 mt-2 mb-0">
          Tienes el {{ puntuacion }}% de los ingredientes<span v-if="faltantes.length">
            y te faltan {{ faltantes.length }}</span
          >.
        </p>
      </v-card>

      <div class="d-flex flex-column flex-sm-row flex-wrap ga-3 mb-6">
        <v-btn
          :color="esFavorita ? 'primary' : undefined"
          :variant="esFavorita ? 'flat' : 'tonal'"
          :prepend-icon="esFavorita ? 'mdi-heart' : 'mdi-heart-outline'"
          :loading="trabajandoFavorito"
          size="large"
          @click="alternarFavorito(receta.external_id)"
        >
          {{ esFavorita ? 'En favoritos' : 'Guardar en favoritos' }}
        </v-btn>
        <v-btn
          color="secondary"
          variant="tonal"
          prepend-icon="mdi-auto-fix"
          size="large"
          @click="adaptar"
          >Adaptar con IA</v-btn
        >
        <v-btn
          variant="tonal"
          prepend-icon="mdi-cart-plus"
          size="large"
          :disabled="!faltantes.length"
          :loading="añadiendoFaltantes"
          @click="añadirFaltantes"
        >
          Añadir faltantes a la lista de compra
        </v-btn>
      </div>

      <section class="mb-6" aria-labelledby="titulo-ingredientes">
        <h2 id="titulo-ingredientes" class="text-h6 mb-2">Ingredientes</h2>
        <v-card variant="flat" border>
          <v-list>
            <v-list-item
              v-for="(i, n) in receta.ingredients"
              :key="n"
              :title="i.ingredient"
              :subtitle="i.measure"
            >
              <template v-if="puntuacion !== null" #prepend>
                <v-icon
                  :icon="
                    faltanSet.has(normalizar(i.ingredient))
                      ? 'mdi-circle-outline'
                      : 'mdi-check-circle'
                  "
                  :color="faltanSet.has(normalizar(i.ingredient)) ? undefined : 'secondary'"
                  :aria-label="faltanSet.has(normalizar(i.ingredient)) ? 'Te falta' : 'Lo tienes'"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </section>

      <section aria-labelledby="titulo-pasos">
        <h2 id="titulo-pasos" class="text-h6 mb-2">Preparación</h2>
        <ol class="pasos pa-0" style="list-style: none">
          <li v-for="(paso, n) in pasos" :key="n" class="d-flex ga-3 mb-4">
            <v-avatar color="primary" size="32" class="flex-shrink-0">{{ n + 1 }}</v-avatar>
            <p class="mb-0">{{ paso }}</p>
          </li>
        </ol>
      </section>
    </article>

    <AdaptRecipeDialog
      v-model="adaptarAbierto"
      :adaptacion="adaptacion"
      :cargando="adaptando"
      :error="adaptacionError"
      @reintentar="adaptar"
    />
    <ConfirmDialog
      v-model="confirmandoFavorito"
      titulo="¿Quitar de favoritos?"
      texto="La receta dejará de aparecer en tus favoritos, junto con tus notas."
      confirmar="Quitar"
      :cargando="trabajandoFavorito"
      @confirmar="confirmarQuitarFavorito"
    />
  </v-container>
</template>
