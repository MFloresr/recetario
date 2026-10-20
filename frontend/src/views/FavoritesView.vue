<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useRecipeStore } from '@/stores/recipe'
import { useUiStore } from '@/stores/ui'
import type { Favorite } from '@/types/api'
import { notificarError } from '@/utils/errores'

const recipes = useRecipeStore()
const ui = useUiStore()

const borradores = reactive<Record<number, string>>({})
const guardando = ref<number | null>(null)
const porQuitar = ref<Favorite | null>(null)
const confirmando = ref(false)
const quitando = ref(false)

onMounted(async () => {
  try {
    await recipes.cargarFavoritos(true)
  } catch (e) {
    notificarError(e)
  }
})

function notas(f: Favorite): string {
  return borradores[f.id] ?? f.notes
}

function cambiadas(f: Favorite): boolean {
  return f.id in borradores && borradores[f.id] !== f.notes
}

async function guardar(f: Favorite) {
  guardando.value = f.id
  try {
    await recipes.guardarNotas(f.id, borradores[f.id] ?? '')
    delete borradores[f.id]
    ui.mostrarAviso('Notas guardadas', 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    guardando.value = null
  }
}

function pedirQuitar(f: Favorite) {
  porQuitar.value = f
  confirmando.value = true
}

async function quitar() {
  if (!porQuitar.value) return
  quitando.value = true
  try {
    await recipes.quitarFavorito(porQuitar.value.id)
    ui.mostrarAviso('Receta quitada de favoritos', 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    quitando.value = false
    confirmando.value = false
    porQuitar.value = null
  }
}
</script>

<template>
  <v-container class="favorites-view py-6" style="max-width: 1100px">
    <h1 class="text-h4 font-weight-bold mb-4">Favoritos</h1>

    <v-row v-if="recipes.cargandoFavoritos && !recipes.favoritosCargados">
      <v-col v-for="n in 3" :key="n" cols="12" sm="6" md="4"
        ><v-skeleton-loader type="card"
      /></v-col>
    </v-row>

    <EmptyState
      v-else-if="!recipes.favoritos.length"
      icono="mdi-heart-outline"
      titulo="Todavía no has guardado recetas"
      texto="Pulsa el corazón de una receta para guardarla aquí junto con tus notas."
    >
      <v-btn color="primary" :to="{ name: 'home' }">Buscar recetas</v-btn>
    </EmptyState>

    <v-row v-else>
      <v-col v-for="f in recipes.favoritos" :key="f.id" cols="12" sm="6" md="4">
        <v-card class="favorite-card d-flex flex-column h-100" variant="elevated" elevation="1">
          <v-img
            :src="f.recipe.image"
            :alt="f.recipe.title"
            height="150"
            cover
            class="bg-surface-variant"
          />
          <v-card-item>
            <v-card-title class="text-wrap">{{ f.recipe.title }}</v-card-title>
            <v-card-subtitle>{{
              [f.recipe.category, f.recipe.area].filter(Boolean).join(' · ')
            }}</v-card-subtitle>
            <div v-if="f.recipe.source === 'ai'" class="d-flex flex-wrap ga-1 mt-2">
              <v-chip size="x-small" prepend-icon="mdi-creation">IA</v-chip>
              <v-chip
                v-if="f.recipe.estimated_minutes"
                size="x-small"
                prepend-icon="mdi-clock-outline"
                >{{ f.recipe.estimated_minutes }} min</v-chip
              >
              <v-chip v-if="f.recipe.difficulty" size="x-small" prepend-icon="mdi-chef-hat">{{
                f.recipe.difficulty
              }}</v-chip>
            </div>
          </v-card-item>
          <v-card-text class="flex-grow-1">
            <v-textarea
              :model-value="notas(f)"
              label="Mis notas"
              variant="outlined"
              density="comfortable"
              rows="2"
              auto-grow
              hide-details
              maxlength="2000"
              @update:model-value="(v: string) => (borradores[f.id] = v)"
            />
            <v-btn
              v-if="cambiadas(f)"
              class="mt-2"
              size="small"
              color="primary"
              variant="tonal"
              :loading="guardando === f.id"
              @click="guardar(f)"
              >Guardar notas</v-btn
            >
          </v-card-text>
          <v-card-actions class="px-4 pb-4">
            <v-btn
              color="primary"
              variant="flat"
              :to="{ name: 'recipe', params: { externalId: f.recipe.external_id } }"
              >Ver receta</v-btn
            >
            <v-spacer />
            <v-btn
              icon="mdi-heart-remove-outline"
              variant="text"
              color="error"
              :aria-label="`Quitar ${f.recipe.title} de favoritos`"
              @click="pedirQuitar(f)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <ConfirmDialog
      v-model="confirmando"
      titulo="¿Quitar de favoritos?"
      :texto="`Se quitará «${porQuitar?.recipe.title ?? ''}» de tus favoritos, junto con tus notas.`"
      confirmar="Quitar"
      :cargando="quitando"
      @confirmar="quitar"
    />
  </v-container>
</template>
