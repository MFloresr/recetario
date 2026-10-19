<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import IngredientAdder from '@/components/IngredientAdder.vue'
import { usePantryStore } from '@/stores/pantry'
import { useUiStore } from '@/stores/ui'
import type { Ingredient } from '@/types/api'
import { agruparPorCategoria } from '@/utils/catalogo'
import { notificarError } from '@/utils/errores'
import { normalizar } from '@/utils/texto'

const pantry = usePantryStore()
const ui = useUiStore()

const filtro = ref('')
const añadiendo = ref(false)
const porEliminar = ref<Ingredient | null>(null)
const confirmando = ref(false)
const eliminando = ref(false)
const editando = ref<Ingredient | null>(null)
const cantidad = ref('')
const guardando = ref(false)
const dialogoCantidad = ref(false)

const grupos = computed(() => {
  const q = normalizar(filtro.value)
  const lista = q ? pantry.items.filter((i) => normalizar(i.name).includes(q)) : pantry.items
  return agruparPorCategoria(lista)
})

onMounted(async () => {
  try {
    await pantry.cargar()
  } catch (e) {
    notificarError(e)
  }
})

async function añadir(nombre: string) {
  añadiendo.value = true
  try {
    await pantry.añadir(nombre)
    ui.mostrarAviso(`${nombre} añadido`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    añadiendo.value = false
  }
}

function abrirCantidad(item: Ingredient) {
  editando.value = item
  cantidad.value = item.quantity
  dialogoCantidad.value = true
}

async function guardarCantidad() {
  if (!editando.value) return
  guardando.value = true
  try {
    await pantry.cambiarCantidad(editando.value.id, cantidad.value.trim())
    ui.mostrarAviso('Cantidad actualizada', 'success')
    dialogoCantidad.value = false
  } catch (e) {
    notificarError(e)
  } finally {
    guardando.value = false
  }
}

function pedirEliminar(item: Ingredient) {
  porEliminar.value = item
  confirmando.value = true
}

async function eliminar() {
  if (!porEliminar.value) return
  eliminando.value = true
  try {
    await pantry.eliminar(porEliminar.value.id)
    ui.mostrarAviso(`${porEliminar.value.name} eliminado`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    eliminando.value = false
    confirmando.value = false
    porEliminar.value = null
  }
}
</script>

<template>
  <v-container class="pantry-view py-6" style="max-width: 800px">
    <h1 class="text-h4 font-weight-bold mb-4">Mi despensa</h1>

    <v-card class="pa-4 mb-4" variant="flat" border>
      <IngredientAdder
        :cargando="añadiendo"
        :existentes="pantry.items.map((i) => i.name)"
        @añadir="añadir"
      />
    </v-card>

    <v-text-field
      v-if="pantry.items.length"
      v-model="filtro"
      label="Buscar en mi despensa"
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      density="comfortable"
      clearable
      hide-details
      class="mb-4"
    />

    <div v-if="pantry.cargando && !pantry.cargado">
      <v-skeleton-loader v-for="n in 3" :key="n" type="list-item-two-line" />
    </div>

    <EmptyState
      v-else-if="!pantry.items.length"
      icono="mdi-fridge-outline"
      titulo="Añade ingredientes para descubrir qué puedes cocinar"
      texto="Empieza por lo básico: arroz, huevos, cebolla…"
    />

    <p v-else-if="!grupos.length" class="text-medium-emphasis text-center py-6">
      Ningún ingrediente coincide con «{{ filtro }}».
    </p>

    <template v-else>
      <v-card v-for="grupo in grupos" :key="grupo.valor" class="mb-4" variant="flat" border>
        <v-card-title class="d-flex align-center text-subtitle-1">
          <v-icon :icon="grupo.icono" class="mr-2" color="secondary" aria-hidden="true" />
          {{ grupo.etiqueta }}
          <v-chip size="x-small" class="ml-2">{{ grupo.items.length }}</v-chip>
        </v-card-title>
        <v-list>
          <v-list-item
            v-for="item in grupo.items"
            :key="item.id"
            :title="item.name"
            :subtitle="item.quantity || 'Sin cantidad'"
          >
            <template #append>
              <v-btn
                icon="mdi-pencil-outline"
                variant="text"
                :aria-label="`Editar la cantidad de ${item.name}`"
                @click="abrirCantidad(item)"
              />
              <v-btn
                icon="mdi-delete-outline"
                variant="text"
                color="error"
                :aria-label="`Eliminar ${item.name}`"
                @click="pedirEliminar(item)"
              />
            </template>
          </v-list-item>
        </v-list>
      </v-card>
    </template>

    <v-dialog v-model="dialogoCantidad" max-width="400">
      <v-card>
        <v-card-title class="pt-5 text-wrap">Cantidad de {{ editando?.name }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="cantidad"
            label="Cantidad (opcional)"
            placeholder="Ej.: 500 g"
            variant="outlined"
            maxlength="50"
            autofocus
            hide-details
            @keyup.enter="guardarCantidad"
          />
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" :disabled="guardando" @click="dialogoCantidad = false"
            >Cancelar</v-btn
          >
          <v-btn color="primary" variant="flat" :loading="guardando" @click="guardarCantidad"
            >Guardar</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      v-model="confirmando"
      titulo="¿Quitar este ingrediente?"
      :texto="`Se eliminará «${porEliminar?.name ?? ''}» de tu despensa.`"
      :cargando="eliminando"
      @confirmar="eliminar"
    />
  </v-container>
</template>
