<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { comprobarApi } from '@/api/client'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const theme = useTheme()
const estadoApi = ref<'comprobando' | 'ok' | 'error'>('comprobando')

const chipApi = computed(() => {
  if (estadoApi.value === 'ok')
    return { color: 'secondary', icono: 'mdi-check-circle', texto: 'API conectada' }
  if (estadoApi.value === 'error')
    return { color: 'error', icono: 'mdi-alert-circle', texto: 'API sin respuesta' }
  return { color: undefined, icono: 'mdi-timer-sand', texto: 'Comprobando API' }
})

// El tema elegido por el usuario manda; sin elección se sigue al sistema
watch(
  () => ui.tema,
  (tema) => {
    if (tema) theme.change(tema)
  },
)

function alternarTema() {
  ui.elegirTema(theme.current.value.dark ? 'light' : 'dark')
}

onMounted(async () => {
  try {
    await comprobarApi()
    estadoApi.value = 'ok'
  } catch {
    estadoApi.value = 'error'
  }
})
</script>

<template>
  <v-app>
    <v-app-bar flat color="surface" border="b">
      <v-app-bar-title class="font-weight-bold text-primary">Recetario</v-app-bar-title>
      <v-chip :color="chipApi.color" :prepend-icon="chipApi.icono" size="small" class="mr-2">
        {{ chipApi.texto }}
      </v-chip>
      <v-btn
        icon="mdi-theme-light-dark"
        aria-label="Cambiar entre tema claro y oscuro"
        @click="alternarTema"
      />
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <v-snackbar v-model="ui.aviso.visible" :color="ui.aviso.color" location="bottom" timeout="4000">
      {{ ui.aviso.texto }}
    </v-snackbar>
  </v-app>
</template>
