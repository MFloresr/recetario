<script setup lang="ts">
import type { AiAdaptation } from '@/types/api'

defineProps<{ adaptacion: AiAdaptation | null; cargando: boolean; error: string }>()
const abierto = defineModel<boolean>({ default: false })
const emit = defineEmits<{ reintentar: [] }>()
</script>

<template>
  <v-dialog v-model="abierto" max-width="640" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center pt-4">
        <v-icon icon="mdi-auto-fix" color="primary" class="mr-2" aria-hidden="true" />
        Adaptar con IA
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" aria-label="Cerrar" @click="abierto = false" />
      </v-card-title>

      <v-card-text>
        <div v-if="cargando" aria-live="polite">
          <p class="text-medium-emphasis mb-3">Adaptando la receta a tu despensa…</p>
          <v-skeleton-loader type="article, article" />
        </div>

        <div v-else-if="error">
          <v-alert type="warning" variant="tonal" class="mb-3">{{ error }}</v-alert>
          <p class="text-body-2 text-medium-emphasis mb-3">Puedes seguir con la receta original.</p>
          <v-btn variant="tonal" prepend-icon="mdi-refresh" @click="emit('reintentar')"
            >Reintentar</v-btn
          >
        </div>

        <div v-else-if="adaptacion">
          <v-alert
            v-for="(aviso, i) in adaptacion.warnings"
            :key="i"
            type="warning"
            variant="tonal"
            density="comfortable"
            class="mb-3"
          >
            {{ aviso }}
          </v-alert>

          <h3 class="text-subtitle-1 font-weight-bold mb-2">Sustituciones</h3>
          <p v-if="!adaptacion.substitutions.length" class="text-medium-emphasis mb-4">
            No hace falta sustituir nada.
          </p>
          <v-list v-else lines="two" class="mb-4 pa-0" bg-color="transparent">
            <v-list-item
              v-for="(s, i) in adaptacion.substitutions"
              :key="i"
              :title="`${s.original} → ${s.substitute}`"
              :subtitle="s.note"
            />
          </v-list>

          <h3 class="text-subtitle-1 font-weight-bold mb-2">Pasos adaptados</h3>
          <ol class="pl-5">
            <li v-for="(paso, i) in adaptacion.adapted_steps" :key="i" class="mb-2">{{ paso }}</li>
          </ol>
          <p class="text-caption text-medium-emphasis mt-4">
            Generado por IA: comprueba que las sustituciones te convencen.
          </p>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
