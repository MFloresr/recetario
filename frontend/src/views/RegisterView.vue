<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { aApiError } from '@/api/client'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const email = ref('')
const username = ref('')
const password = ref('')
const mostrarPassword = ref(false)
const aceptado = ref(false)
const error = ref('')
const errores = ref<Record<string, string>>({})

const reglas = {
  email: [
    (v: string) => !!v.trim() || 'Escribe tu correo',
    (v: string) => /^\S+@\S+\.\S+$/.test(v) || 'Escribe un correo válido',
  ],
  username: [(v: string) => !!v.trim() || 'Elige un nombre de usuario'],
  password: [
    (v: string) => !!v || 'Elige una contraseña',
    (v: string) => v.length >= 8 || 'Debe tener al menos 8 caracteres',
  ],
}

async function enviar() {
  if (!aceptado.value) {
    error.value = 'Para crear la cuenta tienes que aceptar el aviso de privacidad.'
    return
  }
  error.value = ''
  errores.value = {}
  try {
    await auth.registrar({
      email: email.value.trim(),
      username: username.value.trim(),
      password: password.value,
    })
    ui.mostrarAviso('Cuenta creada. ¡Bienvenido a Recetario!', 'success')
    await router.replace('/')
  } catch (e) {
    const err = aApiError(e)
    errores.value = err.fields
    error.value = Object.keys(err.fields).length ? '' : err.message
  }
}
</script>

<template>
  <v-container class="d-flex align-center justify-center" style="min-height: 80vh">
    <v-card class="pa-4 w-100" max-width="440">
      <v-card-title class="text-h5 text-wrap">Crea tu cuenta</v-card-title>
      <v-card-subtitle class="text-wrap"
        >Guarda tu despensa, tus favoritas y tu lista de la compra</v-card-subtitle
      >

      <v-card-text>
        <v-form @submit.prevent="enviar">
          <v-alert v-if="error" type="error" variant="tonal" class="mb-4" role="alert">{{
            error
          }}</v-alert>
          <v-text-field
            v-model="email"
            label="Correo electrónico"
            type="email"
            prepend-inner-icon="mdi-email-outline"
            autocomplete="email"
            variant="outlined"
            :rules="reglas.email"
            :error-messages="errores.email"
            :disabled="auth.cargando"
          />
          <v-text-field
            v-model="username"
            label="Nombre de usuario"
            prepend-inner-icon="mdi-account-outline"
            autocomplete="username"
            variant="outlined"
            :rules="reglas.username"
            :error-messages="errores.username"
            :disabled="auth.cargando"
          />
          <v-text-field
            v-model="password"
            label="Contraseña"
            prepend-inner-icon="mdi-lock-outline"
            :type="mostrarPassword ? 'text' : 'password'"
            autocomplete="new-password"
            variant="outlined"
            hint="Mínimo 8 caracteres, no demasiado común"
            :rules="reglas.password"
            :error-messages="errores.password"
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
          <v-checkbox
            v-model="aceptado"
            density="compact"
            hide-details
            class="mb-3"
            :disabled="auth.cargando"
          >
            <template #label>
              <span>
                He leído el
                <router-link :to="{ name: 'privacy' }" target="_blank" @click.stop
                  >aviso de privacidad</router-link
                >
                y lo acepto
              </span>
            </template>
          </v-checkbox>
          <v-btn
            type="submit"
            color="primary"
            size="x-large"
            block
            :loading="auth.cargando"
            :disabled="auth.cargando"
            >Crear cuenta</v-btn
          >
        </v-form>
      </v-card-text>

      <v-card-actions class="justify-center pb-4">
        <span class="text-medium-emphasis">¿Ya tienes cuenta?</span>
        <v-btn variant="text" color="primary" :to="{ name: 'login' }">Entrar</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
