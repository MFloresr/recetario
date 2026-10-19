<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <v-container class="py-8">
    <h1 class="text-h5 mb-2">{{ route.meta.titulo }}</h1>
    <p class="text-medium-emphasis">Esta pantalla se construye en una fase posterior.</p>
  </v-container>
</template>
