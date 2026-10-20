<script setup lang="ts">
import type { AiSuggestion } from '@/types/api'
import { TIPOS_PARA_IA, tipoComida } from '@/utils/catalogo'

defineProps<{
  sugerencias: AiSuggestion[]
  cargando: boolean
  error: string
  /** Títulos de las recetas de la IA que ya están en el recetario. */
  guardadas?: string[]
  guardando?: string | null
}>()
const abierto = defineModel<boolean>({ default: false })
const tipo = defineModel<string>('tipo', { default: '' })
const consulta = defineModel<string>('consulta', { default: '' })
const emit = defineEmits<{
  reintentar: []
  buscar: []
  guardar: [sugerencia: AiSuggestion]
  'añadir-faltantes': [sugerencia: AiSuggestion]
  abrir: [sugerencia: AiSuggestion]
}>()

function estaGuardada(s: AiSuggestion, guardadas?: string[]): boolean {
  return Boolean(s.saved) || Boolean(guardadas?.includes(s.title))
}

const COLOR_DIFICULTAD: Record<string, string> = {
  fácil: 'success',
  media: 'warning',
  difícil: 'error',
}

function minutos(m: number): string {
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const resto = m % 60
  return resto ? `${h} h ${resto} min` : `${h} h`
}
</script>

<template>
  <v-dialog v-model="abierto" max-width="720" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center pt-4">
        <v-icon icon="mdi-creation" color="primary" class="mr-2" aria-hidden="true" />
        Recetas con IA
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" aria-label="Cerrar" @click="abierto = false" />
      </v-card-title>

      <div class="px-6 pb-2">
        <form class="d-flex align-start ga-2 mb-3" @submit.prevent="emit('buscar')">
          <v-text-field
            v-model="consulta"
            label="Busca una receta concreta"
            placeholder="Ej.: lasaña, tarta de queso, gazpacho"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="comfortable"
            hide-details
            maxlength="120"
            :disabled="cargando"
          />
          <v-btn
            type="submit"
            color="primary"
            size="large"
            icon="mdi-send"
            aria-label="Buscar con la IA"
            :disabled="cargando"
          />
        </form>
        <p class="text-body-2 text-medium-emphasis mb-2">
          Déjalo vacío para que te proponga ideas con lo que tienes en casa. ¿Qué te apetece?
        </p>
        <v-chip-group
          v-model="tipo"
          mandatory
          selected-class="text-primary"
          column
          :disabled="cargando"
        >
          <v-chip value="" variant="outlined" filter>Cualquiera</v-chip>
          <v-chip
            v-for="t in TIPOS_PARA_IA"
            :key="t.valor"
            :value="t.valor"
            :prepend-icon="t.icono"
            variant="outlined"
            filter
          >
            {{ t.etiqueta }}
          </v-chip>
        </v-chip-group>
      </div>

      <v-card-text>
        <div v-if="cargando" aria-live="polite">
          <p class="text-medium-emphasis mb-3">La IA está buscando recetas…</p>
          <v-skeleton-loader v-for="n in 2" :key="n" type="image, article" class="mb-3" />
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

        <div v-else-if="sugerencias.length" class="d-flex flex-column ga-4">
          <v-card v-for="(s, i) in sugerencias" :key="i" class="ai-recipe" variant="outlined">
            <v-img
              v-if="s.image"
              :src="s.image.url"
              :alt="`Foto orientativa de ${s.title}`"
              height="180"
              cover
              class="foto-receta"
            />

            <v-card-item>
              <v-card-title class="text-wrap">{{ s.title }}</v-card-title>
              <v-card-subtitle v-if="s.description" class="text-wrap">{{
                s.description
              }}</v-card-subtitle>
            </v-card-item>

            <v-card-text class="pt-0">
              <div class="d-flex flex-wrap ga-2 mb-3">
                <v-chip
                  v-if="tipoComida(s.meal_type)"
                  size="small"
                  color="secondary"
                  variant="tonal"
                  :prepend-icon="tipoComida(s.meal_type)?.icono"
                >
                  {{ tipoComida(s.meal_type)?.etiqueta }}
                </v-chip>
                <v-chip v-if="s.estimated_minutes" size="small" prepend-icon="mdi-clock-outline">{{
                  minutos(s.estimated_minutes)
                }}</v-chip>
                <v-chip v-if="s.prep_minutes" size="small" prepend-icon="mdi-knife"
                  >Preparación {{ minutos(s.prep_minutes) }}</v-chip
                >
                <v-chip v-if="s.cook_minutes" size="small" prepend-icon="mdi-stove"
                  >Cocción {{ minutos(s.cook_minutes) }}</v-chip
                >
                <v-chip
                  v-if="s.difficulty"
                  size="small"
                  prepend-icon="mdi-chef-hat"
                  :color="COLOR_DIFICULTAD[s.difficulty]"
                  variant="tonal"
                >
                  Dificultad {{ s.difficulty }}
                </v-chip>
                <v-chip v-if="s.servings" size="small" prepend-icon="mdi-account-multiple-outline"
                  >{{ s.servings }} {{ s.servings === 1 ? 'ración' : 'raciones' }}</v-chip
                >
              </div>

              <v-expansion-panels variant="accordion" flat>
                <v-expansion-panel title="Ingredientes">
                  <template #text>
                    <ul v-if="s.ingredients.length" class="pl-0" style="list-style: none">
                      <li v-for="(ing, j) in s.ingredients" :key="j" class="mb-1">
                        <strong>{{ ing.quantity }}</strong> {{ ing.name }}
                      </li>
                    </ul>
                    <p v-else-if="s.ingredients_used.length" class="mb-0">
                      {{ s.ingredients_used.join(', ') }}
                    </p>
                    <p v-if="s.missing_ingredients.length" class="text-body-2 mt-3 mb-0">
                      <strong class="text-error">Te falta:</strong>
                      {{ s.missing_ingredients.join(', ') }}
                    </p>
                  </template>
                </v-expansion-panel>
                <v-expansion-panel title="Preparación">
                  <template #text>
                    <ol class="pl-5">
                      <li v-for="(paso, j) in s.steps" :key="j" class="mb-3">
                        {{ paso.text }}
                        <v-chip
                          v-if="paso.minutes"
                          size="x-small"
                          class="ml-1"
                          prepend-icon="mdi-timer-outline"
                          >{{ minutos(paso.minutes) }}</v-chip
                        >
                      </li>
                    </ol>
                    <div v-if="s.tips.length" class="mt-3">
                      <p class="font-weight-bold mb-1">Consejos</p>
                      <ul class="pl-5">
                        <li v-for="(consejo, j) in s.tips" :key="j" class="mb-1">{{ consejo }}</li>
                      </ul>
                    </div>
                  </template>
                </v-expansion-panel>
              </v-expansion-panels>

              <p v-if="s.image" class="text-caption text-medium-emphasis mt-3 mb-0">
                Foto orientativa:
                <a :href="s.image.page" target="_blank" rel="noopener">{{ s.image.credit }}</a>
              </p>
            </v-card-text>

            <v-card-actions class="px-4 pb-4 flex-wrap ga-2">
              <template v-if="estaGuardada(s, guardadas)">
                <v-btn variant="tonal" color="primary" prepend-icon="mdi-check" disabled>
                  Guardada en tu recetario
                </v-btn>
                <v-btn
                  v-if="s.external_id"
                  variant="flat"
                  color="primary"
                  prepend-icon="mdi-open-in-new"
                  @click="emit('abrir', s)"
                >
                  Abrir receta
                </v-btn>
              </template>
              <v-btn
                v-else
                variant="flat"
                color="primary"
                prepend-icon="mdi-heart-outline"
                :loading="guardando === s.title"
                :disabled="Boolean(guardando)"
                @click="emit('guardar', s)"
              >
                Guardar en mi recetario
              </v-btn>
              <v-btn
                v-if="s.missing_ingredients.length"
                variant="tonal"
                prepend-icon="mdi-cart-plus"
                @click="emit('añadir-faltantes', s)"
              >
                Añadir lo que falta a la compra
              </v-btn>
            </v-card-actions>
          </v-card>

          <p class="text-caption text-medium-emphasis">
            Las recetas que genera la IA se guardan solas en «Mis recetas» para que las veas otro
            día. Recetas generadas por una IA a partir de lo que sabe (no está navegando por
            internet): revisa cantidades y tiempos antes de cocinar.
          </p>
        </div>

        <p v-else class="text-medium-emphasis">
          Escribe una receta arriba o añade ingredientes en la pantalla de inicio para que la IA te
          proponga ideas.
        </p>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
