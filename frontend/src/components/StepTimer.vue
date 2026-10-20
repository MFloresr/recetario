<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps<{ minutos: number }>()

const total = computed(() => props.minutos * 60)
const restante = ref(props.minutos * 60)
const corriendo = ref(false)
const terminado = ref(false)
let reloj: ReturnType<typeof setInterval> | null = null

const texto = computed(() => {
  const m = Math.floor(restante.value / 60)
  const s = restante.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

function pitar() {
  try {
    const Audio =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new Audio()
    for (let i = 0; i < 3; i++) {
      const o = ctx.createOscillator()
      const g = ctx.createGain()
      o.frequency.value = 880
      g.gain.value = 0.15
      o.connect(g)
      g.connect(ctx.destination)
      o.start(ctx.currentTime + i * 0.35)
      o.stop(ctx.currentTime + i * 0.35 + 0.2)
    }
  } catch {
    // Sin audio: queda el aviso en pantalla y la vibración
  }
  navigator.vibrate?.([300, 150, 300, 150, 300])
}

function parar() {
  if (reloj) clearInterval(reloj)
  reloj = null
  corriendo.value = false
}

function iniciar() {
  if (corriendo.value) return
  if (terminado.value) reiniciar()
  corriendo.value = true
  reloj = setInterval(() => {
    restante.value -= 1
    if (restante.value <= 0) {
      restante.value = 0
      parar()
      terminado.value = true
      pitar()
    }
  }, 1000)
}

function reiniciar() {
  parar()
  restante.value = total.value
  terminado.value = false
}

onBeforeUnmount(parar)
</script>

<template>
  <div class="step-timer d-inline-flex align-center ga-2 flex-wrap">
    <v-btn
      v-if="!corriendo"
      size="small"
      variant="tonal"
      color="secondary"
      prepend-icon="mdi-timer-outline"
      :aria-label="`Iniciar temporizador de ${minutos} minutos`"
      @click="iniciar"
    >
      {{ terminado ? 'Repetir' : restante < total ? `Seguir ${texto}` : `${minutos} min` }}
    </v-btn>
    <v-btn
      v-else
      size="small"
      variant="flat"
      color="secondary"
      prepend-icon="mdi-pause"
      aria-label="Pausar el temporizador"
      @click="parar"
    >
      <span class="tiempo">{{ texto }}</span>
    </v-btn>
    <v-btn
      v-if="restante < total && !corriendo"
      size="small"
      variant="text"
      icon="mdi-restart"
      aria-label="Reiniciar el temporizador"
      @click="reiniciar"
    />
    <span v-if="terminado" class="text-body-2 font-weight-bold text-success" role="status"
      >¡Tiempo cumplido!</span
    >
  </div>
</template>
