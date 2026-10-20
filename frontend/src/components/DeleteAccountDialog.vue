<script setup lang="ts">
import { ref, watch } from 'vue'
import { aApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const abierto = defineModel<boolean>({ default: false })
const emit = defineEmits<{ eliminada: [] }>()

const auth = useAuthStore()
const password = ref('')
const mostrar = ref(false)
const error = ref('')
const eliminando = ref(false)

watch(abierto, (valor) => {
  if (valor) {
    password.value = ''
    error.value = ''
    mostrar.value = false
  }
})

async function eliminar() {
  if (!password.value) {
    error.value = 'Escribe tu contraseña para confirmar.'
    return
  }
  eliminando.value = true
  error.value = ''
  try {
    await auth.eliminarCuenta(password.value)
    abierto.value = false
    emit('eliminada')
  } catch (e) {
    const err = aApiError(e)
    error.value = err.fields.password ?? err.message
  } finally {
    eliminando.value = false
  }
}
</script>

<template>
  <v-dialog v-model="abierto" max-width="440" :persistent="eliminando">
    <v-card>
      <v-card-title class="text-wrap pt-5">¿Eliminar tu cuenta?</v-card-title>
      <v-card-text>
        <p class="mb-4">
          Se borrarán para siempre tu cuenta, tu despensa, tu lista de la compra y tus favoritos con
          sus notas. No se puede deshacer.
        </p>
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          density="compact"
          class="mb-3"
          role="alert"
          >{{ error }}</v-alert
        >
        <v-form @submit.prevent="eliminar">
          <v-text-field
            v-model="password"
            label="Tu contraseña"
            :type="mostrar ? 'text' : 'password'"
            autocomplete="current-password"
            variant="outlined"
            hide-details
            :disabled="eliminando"
          >
            <template #append-inner>
              <v-btn
                :icon="mostrar ? 'mdi-eye-off' : 'mdi-eye'"
                :aria-label="mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                variant="text"
                size="small"
                @click="mostrar = !mostrar"
              />
            </template>
          </v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" :disabled="eliminando" @click="abierto = false">Cancelar</v-btn>
        <v-btn color="error" variant="flat" :loading="eliminando" @click="eliminar"
          >Eliminar cuenta</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
