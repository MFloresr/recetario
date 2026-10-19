<script setup lang="ts">
import { computed, ref } from 'vue'
import { INGREDIENTES_FRECUENTES } from '@/utils/catalogo'
import { normalizar } from '@/utils/texto'

const props = withDefaults(
  defineProps<{ cargando?: boolean; etiqueta?: string; existentes?: string[] }>(),
  { cargando: false, etiqueta: 'Añadir ingrediente', existentes: () => [] },
)
const emit = defineEmits<{ añadir: [nombre: string] }>()

const texto = ref('')

/** Ingredientes frecuentes que aún no están añadidos y encajan con lo escrito (máx. 8). */
const sugerencias = computed(() => {
  const q = normalizar(texto.value)
  const tengo = new Set(props.existentes.map(normalizar))
  return INGREDIENTES_FRECUENTES.filter(
    (s) => !tengo.has(normalizar(s)) && normalizar(s).includes(q),
  ).slice(0, 8)
})

function enviar(nombre: string) {
  const limpio = nombre.trim()
  if (!limpio || props.cargando) return
  emit('añadir', limpio)
  texto.value = ''
}
</script>

<template>
  <div class="ingredient-adder">
    <form class="d-flex align-start ga-2" @submit.prevent="enviar(texto)">
      <v-text-field
        v-model="texto"
        :label="etiqueta"
        prepend-inner-icon="mdi-food-apple-outline"
        variant="outlined"
        density="comfortable"
        hide-details
        maxlength="100"
        autocomplete="off"
        enterkeyhint="done"
      />
      <v-btn
        type="submit"
        color="primary"
        size="large"
        icon="mdi-plus"
        aria-label="Añadir ingrediente"
        :disabled="!texto.trim() || cargando"
        :loading="cargando"
      />
    </form>
    <div
      v-if="sugerencias.length"
      class="d-flex flex-wrap ga-2 mt-3"
      role="group"
      aria-label="Ingredientes frecuentes"
    >
      <v-chip
        v-for="s in sugerencias"
        :key="s"
        size="small"
        variant="outlined"
        prepend-icon="mdi-plus"
        :disabled="cargando"
        @click="enviar(s)"
      >
        {{ s }}
      </v-chip>
    </div>
  </div>
</template>
