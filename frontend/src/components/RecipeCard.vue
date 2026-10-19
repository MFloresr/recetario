<script setup lang="ts">
import { computed } from 'vue'
import type { RecipeSummary } from '@/types/api'
import { tipoComida } from '@/utils/catalogo'

const props = defineProps<{ receta: RecipeSummary; favorita: boolean; guardando?: boolean }>()
const emit = defineEmits<{ 'alternar-favorito': [] }>()

const MAX_VISIBLES = 6

function resumir(lista: string[]): string {
  const visibles = lista.slice(0, MAX_VISIBLES).join(', ')
  return lista.length > MAX_VISIBLES ? `${visibles} y ${lista.length - MAX_VISIBLES} más` : visibles
}

const color = computed(() =>
  props.receta.match_score >= 75
    ? 'secondary'
    : props.receta.match_score >= 40
      ? 'warning'
      : 'error',
)
const tipo = computed(() => tipoComida(props.receta.meal_type))
const origen = computed(() =>
  [props.receta.category, props.receta.area].filter(Boolean).join(' · '),
)
</script>

<template>
  <v-card class="recipe-card d-flex flex-column h-100" variant="elevated" elevation="1">
    <v-img :src="receta.image" :alt="receta.title" height="170" cover class="bg-surface-variant">
      <template #placeholder>
        <div class="d-flex align-center justify-center fill-height">
          <v-icon icon="mdi-silverware-fork-knife" size="40" />
        </div>
      </template>
    </v-img>

    <v-card-item>
      <v-card-title class="text-wrap">{{ receta.title }}</v-card-title>
      <v-card-subtitle v-if="origen">{{ origen }}</v-card-subtitle>
      <v-chip
        v-if="tipo"
        class="mt-2"
        size="small"
        :prepend-icon="tipo.icono"
        variant="tonal"
        color="secondary"
        >{{ tipo.etiqueta }}</v-chip
      >
    </v-card-item>

    <v-card-text class="flex-grow-1 pt-0">
      <div class="d-flex align-center ga-3 mb-3">
        <v-progress-linear
          :model-value="receta.match_score"
          :color="color"
          height="10"
          rounded
          aria-hidden="true"
        />
        <strong class="match-score text-no-wrap">{{ receta.match_score }}%</strong>
      </div>
      <p class="text-caption text-medium-emphasis mb-2">
        {{ receta.match_score }}% de ingredientes disponibles
      </p>
      <p v-if="receta.matched_ingredients.length" class="text-body-2 mb-1">
        <strong class="text-secondary">Tienes:</strong> {{ resumir(receta.matched_ingredients) }}
      </p>
      <p v-if="receta.missing_ingredients.length" class="text-body-2">
        <strong class="text-error">Te falta:</strong> {{ resumir(receta.missing_ingredients) }}
      </p>
      <p v-else class="text-body-2 text-secondary">¡No te falta nada!</p>
    </v-card-text>

    <v-card-actions class="px-4 pb-4">
      <v-btn
        color="primary"
        variant="flat"
        :to="{ name: 'recipe', params: { externalId: receta.external_id } }"
        >Ver receta</v-btn
      >
      <v-spacer />
      <v-btn
        :icon="favorita ? 'mdi-heart' : 'mdi-heart-outline'"
        :color="favorita ? 'primary' : undefined"
        :loading="guardando"
        :aria-label="favorita ? 'Quitar de favoritos' : 'Guardar en favoritos'"
        :aria-pressed="favorita"
        variant="text"
        @click="emit('alternar-favorito')"
      />
    </v-card-actions>
  </v-card>
</template>
