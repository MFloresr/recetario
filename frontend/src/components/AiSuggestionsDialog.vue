<script setup lang="ts">
import type { AiSuggestion } from '@/types/api'

defineProps<{ sugerencias: AiSuggestion[]; cargando: boolean; error: string }>()
const abierto = defineModel<boolean>({ default: false })
const emit = defineEmits<{ reintentar: [] }>()
</script>

<template>
  <v-dialog v-model="abierto" max-width="640" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center pt-4">
        <v-icon icon="mdi-creation" color="primary" class="mr-2" aria-hidden="true" />
        Ideas con IA
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" aria-label="Cerrar" @click="abierto = false" />
      </v-card-title>

      <v-card-text>
        <div v-if="cargando" aria-live="polite">
          <p class="text-medium-emphasis mb-3">La IA está pensando qué puedes cocinar…</p>
          <v-skeleton-loader v-for="n in 3" :key="n" type="article" class="mb-3" />
        </div>

        <div v-else-if="error">
          <v-alert type="warning" variant="tonal" class="mb-3">{{ error }}</v-alert>
          <p class="text-body-2 text-medium-emphasis mb-3">
            La búsqueda normal de recetas sigue funcionando.
          </p>
          <v-btn variant="tonal" prepend-icon="mdi-refresh" @click="emit('reintentar')"
            >Reintentar</v-btn
          >
        </div>

        <div v-else-if="sugerencias.length">
          <v-expansion-panels variant="accordion">
            <v-expansion-panel v-for="(s, i) in sugerencias" :key="i" :title="s.title">
              <template #text>
                <p v-if="s.description" class="mb-3">{{ s.description }}</p>
                <div class="d-flex flex-wrap ga-2 mb-3">
                  <v-chip v-if="s.estimated_minutes" size="small" prepend-icon="mdi-clock-outline"
                    >{{ s.estimated_minutes }} min</v-chip
                  >
                  <v-chip v-if="s.difficulty" size="small" prepend-icon="mdi-chef-hat">{{
                    s.difficulty
                  }}</v-chip>
                </div>
                <p v-if="s.ingredients_used.length" class="text-body-2 mb-1">
                  <strong class="text-secondary">Usas:</strong> {{ s.ingredients_used.join(', ') }}
                </p>
                <p v-if="s.missing_ingredients.length" class="text-body-2 mb-3">
                  <strong class="text-error">Te falta:</strong>
                  {{ s.missing_ingredients.join(', ') }}
                </p>
                <ol class="pl-5">
                  <li v-for="(paso, j) in s.steps" :key="j" class="mb-1">{{ paso }}</li>
                </ol>
              </template>
            </v-expansion-panel>
          </v-expansion-panels>
          <p class="text-caption text-medium-emphasis mt-4">
            Son ideas generadas por una IA: revisa los pasos y las cantidades antes de cocinar.
          </p>
        </div>

        <p v-else class="text-medium-emphasis">La IA no ha propuesto nada con esos ingredientes.</p>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
