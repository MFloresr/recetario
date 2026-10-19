<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { mensajeDeError } from '@/utils/errores'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const identificador = ref('')
const password = ref('')
const mostrarPassword = ref(false)
const error = ref('')

const reglas = {
  identificador: [(v: string) => !!v.trim() || 'Escribe tu correo o tu usuario'],
  password: [(v: string) => !!v || 'Escribe tu contraseña'],
}

async function enviar() {
  if (!identificador.value.trim() || !password.value) return
  error.value = ''
  try {
    await auth.iniciarSesion(identificador.value, password.value)
    const destino =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    await router.replace(destino)
  } catch (e) {
    error.value = mensajeDeError(e)
  }
}
</script>

<template>
  <v-container class="d-flex align-center justify-center" style="min-height: 80vh">
    <v-card class="pa-4 w-100" max-width="440">
      <v-card-title class="text-h5 text-wrap">Entra en Recetario</v-card-title>
      <v-card-subtitle class="text-wrap">Cocina con lo que tienes en casa</v-card-subtitle>

      <v-card-text>
        <v-form class="login-form" @submit.prevent="enviar">
          <v-alert v-if="error" type="error" variant="tonal" class="mb-4" role="alert">{{
            error
          }}</v-alert>
          <v-text-field
            v-model="identificador"
            label="Correo o usuario"
            prepend-inner-icon="mdi-account-outline"
            autocomplete="username"
            variant="outlined"
            :rules="reglas.identificador"
            :disabled="auth.cargando"
          />
          <v-text-field
            v-model="password"
            label="Contraseña"
            prepend-inner-icon="mdi-lock-outline"
            :type="mostrarPassword ? 'text' : 'password'"
            autocomplete="current-password"
            variant="outlined"
            :rules="reglas.password"
            :disabled="auth.cargando"
          >
            <template #append-inner>
              <v-btn
                :icon="mostrarPassword ? 'mdi-eye-off' : 'mdi-eye'"
                :aria-label="mostrarPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                variant="text"
                size="small"
                @click="mostrarPassword = !mostrarPassword"
              />
            </template>
          </v-text-field>
          <v-btn
            type="submit"
            color="primary"
            size="x-large"
            block
            :loading="auth.cargando"
            :disabled="auth.cargando"
            >Entrar</v-btn
          >
        </v-form>
      </v-card-text>

      <v-card-actions class="justify-center pb-4">
        <span class="text-medium-emphasis">¿No tienes cuenta?</span>
        <v-btn variant="text" color="primary" :to="{ name: 'register' }">Crear cuenta</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
