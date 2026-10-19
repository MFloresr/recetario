<script setup lang="ts">
defineProps<{ nombre: string; cantidad?: string }>()
const emit = defineEmits<{ quitar: [] }>()
</script>

<template>
  <v-chip
    class="ingredient-chip"
    color="primary"
    variant="tonal"
    size="large"
    closable
    :close-label="`Quitar ${nombre}`"
    @click:close="emit('quitar')"
  >
    {{ nombre }}<span v-if="cantidad" class="text-medium-emphasis ml-1">· {{ cantidad }}</span>
  </v-chip>
</template>
