<script setup lang="ts">
withDefaults(
  defineProps<{ titulo: string; texto: string; confirmar?: string; cargando?: boolean }>(),
  { confirmar: 'Eliminar', cargando: false },
)
const abierto = defineModel<boolean>({ default: false })
const emit = defineEmits<{ confirmar: [] }>()
</script>

<template>
  <v-dialog v-model="abierto" max-width="420" :persistent="cargando">
    <v-card>
      <v-card-title class="text-wrap pt-5">{{ titulo }}</v-card-title>
      <v-card-text>{{ texto }}</v-card-text>
      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" :disabled="cargando" @click="abierto = false">Cancelar</v-btn>
        <v-btn color="error" variant="flat" :loading="cargando" @click="emit('confirmar')">{{
          confirmar
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
