<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { usePantryStore } from '@/stores/pantry'
import { useRecipeStore } from '@/stores/recipe'
import { useShoppingListStore } from '@/stores/shoppingList'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const auth = useAuthStore()
const pantry = usePantryStore()
const recipes = useRecipeStore()
const shopping = useShoppingListStore()
const theme = useTheme()
const router = useRouter()
const route = useRoute()
const { mdAndUp } = useDisplay()
const borrandoCuenta = ref(false)

const enlaces = [
  {
    nombre: 'home',
    texto: 'Inicio',
    icono: 'mdi-home-variant-outline',
    iconoActivo: 'mdi-home-variant',
  },
  { nombre: 'pantry', texto: 'Despensa', icono: 'mdi-fridge-outline', iconoActivo: 'mdi-fridge' },
  { nombre: 'shopping-list', texto: 'Compra', icono: 'mdi-cart-outline', iconoActivo: 'mdi-cart' },
  { nombre: 'favorites', texto: 'Favoritos', icono: 'mdi-heart-outline', iconoActivo: 'mdi-heart' },
] as const

const mostrarNavegacion = computed(() => auth.autenticado && !route.meta.soloInvitados)
const cargando = computed(() => ui.peticiones > 0)

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

function salir() {
  auth.cerrarSesion()
  pantry.vaciar()
  recipes.vaciar()
  shopping.vaciar()
  void router.replace({ name: 'login' })
}

function cuentaEliminada() {
  pantry.vaciar()
  recipes.vaciar()
  shopping.vaciar()
  ui.mostrarAviso('Tu cuenta y tus datos se han eliminado.', 'success')
  void router.replace({ name: 'login' })
}

function sesionCaducada() {
  pantry.vaciar()
  recipes.vaciar()
  shopping.vaciar()
  ui.mostrarAviso('Tu sesión ha caducado. Vuelve a entrar.', 'info')
  void router.replace({ name: 'login' })
}

onMounted(() => {
  window.addEventListener('recetario:sesion-caducada', sesionCaducada)
  void auth.cargarUsuario()
})
onBeforeUnmount(() => window.removeEventListener('recetario:sesion-caducada', sesionCaducada))
</script>

<template>
  <v-app>
    <v-app-bar flat color="surface" border="b">
      <v-app-bar-title class="font-weight-bold text-primary">
        <v-icon icon="mdi-chef-hat" class="mr-1" aria-hidden="true" />Recetario
      </v-app-bar-title>
      <v-btn
        icon="mdi-theme-light-dark"
        aria-label="Cambiar entre tema claro y oscuro"
        @click="alternarTema"
      />
      <v-menu v-if="auth.autenticado">
        <template #activator="{ props }">
          <v-btn v-bind="props" icon="mdi-account-circle-outline" aria-label="Mi cuenta" />
        </template>
        <v-list>
          <v-list-item :title="auth.user?.username ?? 'Mi cuenta'" :subtitle="auth.user?.email" />
          <v-divider />
          <v-list-item
            prepend-icon="mdi-shield-lock-outline"
            title="Privacidad"
            :to="{ name: 'privacy' }"
          />
          <v-list-item prepend-icon="mdi-logout" title="Cerrar sesión" @click="salir" />
          <v-list-item
            prepend-icon="mdi-account-remove-outline"
            title="Eliminar mi cuenta"
            base-color="error"
            @click="borrandoCuenta = true"
          />
        </v-list>
      </v-menu>
      <v-progress-linear
        v-if="cargando"
        indeterminate
        color="primary"
        absolute
        location="bottom"
        aria-label="Cargando"
      />
    </v-app-bar>

    <v-navigation-drawer v-if="mostrarNavegacion && mdAndUp" permanent>
      <v-list nav class="mt-2">
        <v-list-item
          v-for="e in enlaces"
          :key="e.nombre"
          :to="{ name: e.nombre }"
          :prepend-icon="e.icono"
          :title="e.texto"
          rounded="xl"
          color="primary"
        >
          <template v-if="e.nombre === 'shopping-list' && shopping.pendientes" #append>
            <v-badge :content="shopping.pendientes" color="primary" inline />
          </template>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>

    <v-bottom-navigation v-if="mostrarNavegacion && !mdAndUp" grow color="primary" :elevation="3">
      <v-btn v-for="e in enlaces" :key="e.nombre" :to="{ name: e.nombre }" :aria-label="e.texto">
        <v-badge
          v-if="e.nombre === 'shopping-list' && shopping.pendientes"
          :content="shopping.pendientes"
          color="primary"
        >
          <v-icon :icon="e.icono" />
        </v-badge>
        <v-icon v-else :icon="e.icono" />
        <span>{{ e.texto }}</span>
      </v-btn>
    </v-bottom-navigation>

    <DeleteAccountDialog v-model="borrandoCuenta" @eliminada="cuentaEliminada" />

    <v-snackbar
      v-model="ui.aviso.visible"
      :color="ui.aviso.color"
      location="bottom"
      timeout="4000"
      :class="{ 'mb-14': !mdAndUp && mostrarNavegacion }"
    >
      {{ ui.aviso.texto }}
    </v-snackbar>
  </v-app>
</template>
