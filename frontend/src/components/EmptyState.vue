<script setup lang="ts">
defineProps<{ icono: string; titulo: string; texto?: string }>()
</script>

<template>
  <div class="d-flex flex-column align-center text-center py-10 px-4" role="status">
    <v-icon :icon="icono" size="64" color="primary" class="mb-4" aria-hidden="true" />
    <h2 class="text-h6 mb-1">{{ titulo }}</h2>
    <p v-if="texto" class="text-medium-emphasis mb-4" style="max-width: 420px">{{ texto }}</p>
    <slot />
  </div>
</template>
