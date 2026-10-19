<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useShoppingListStore } from '@/stores/shoppingList'
import { useUiStore } from '@/stores/ui'
import type { ShoppingItem } from '@/types/api'
import { agruparPorCategoria } from '@/utils/catalogo'
import { notificarError } from '@/utils/errores'

const shopping = useShoppingListStore()
const ui = useUiStore()

const nuevo = ref('')
const añadiendo = ref(false)
const porEliminar = ref<ShoppingItem | null>(null)
const confirmando = ref(false)
const eliminando = ref(false)
const confirmandoLimpiar = ref(false)
const limpiando = ref(false)

const grupos = computed(() => agruparPorCategoria(shopping.items))

onMounted(async () => {
  try {
    await shopping.cargar()
  } catch (e) {
    notificarError(e)
  }
})

async function añadir() {
  const nombre = nuevo.value.trim()
  if (!nombre) return
  añadiendo.value = true
  try {
    await shopping.añadir(nombre)
    nuevo.value = ''
  } catch (e) {
    notificarError(e)
  } finally {
    añadiendo.value = false
  }
}

async function marcar(item: ShoppingItem, comprado: boolean | null) {
  try {
    await shopping.marcar(item.id, Boolean(comprado))
  } catch (e) {
    notificarError(e)
  }
}

function pedirEliminar(item: ShoppingItem) {
  porEliminar.value = item
  confirmando.value = true
}

async function eliminar() {
  if (!porEliminar.value) return
  eliminando.value = true
  try {
    await shopping.eliminar(porEliminar.value.id)
  } catch (e) {
    notificarError(e)
  } finally {
    eliminando.value = false
    confirmando.value = false
    porEliminar.value = null
  }
}

async function limpiar() {
  limpiando.value = true
  try {
    const n = await shopping.limpiarComprados()
    ui.mostrarAviso(`${n} producto${n === 1 ? '' : 's'} eliminado${n === 1 ? '' : 's'}`, 'success')
  } catch (e) {
    notificarError(e)
  } finally {
    limpiando.value = false
    confirmandoLimpiar.value = false
  }
}
</script>

<template>
  <v-container class="shopping-view py-6" style="max-width: 800px">
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <h1 class="text-h4 font-weight-bold">Lista de la compra</h1>
      <v-chip v-if="shopping.items.length" class="pendientes" color="primary" variant="tonal">
        {{ shopping.pendientes }} pendiente{{ shopping.pendientes === 1 ? '' : 's' }}
      </v-chip>
    </div>

    <v-card class="pa-4 mb-4" variant="flat" border>
      <form class="d-flex align-start ga-2" @submit.prevent="añadir">
        <v-text-field
          v-model="nuevo"
          label="Añadir a la lista"
          prepend-inner-icon="mdi-cart-plus"
          variant="outlined"
          density="comfortable"
          hide-details
          maxlength="100"
          enterkeyhint="done"
        />
        <v-btn
          type="submit"
          color="primary"
          size="large"
          icon="mdi-plus"
          aria-label="Añadir a la lista"
          :disabled="!nuevo.trim() || añadiendo"
          :loading="añadiendo"
        />
      </form>
    </v-card>

    <div v-if="shopping.cargando && !shopping.cargado">
      <v-skeleton-loader v-for="n in 3" :key="n" type="list-item-two-line" />
    </div>

    <EmptyState
      v-else-if="!shopping.items.length"
      icono="mdi-cart-outline"
      titulo="Tu lista de la compra está vacía"
      texto="Desde una receta puedes añadir de una vez los ingredientes que te faltan."
    />

    <template v-else>
      <v-card v-for="grupo in grupos" :key="grupo.valor" class="mb-4" variant="flat" border>
        <v-card-title class="d-flex align-center text-subtitle-1">
          <v-icon :icon="grupo.icono" class="mr-2" color="secondary" aria-hidden="true" />
          {{ grupo.etiqueta }}
        </v-card-title>
        <v-list>
          <v-list-item v-for="item in grupo.items" :key="item.id" class="shopping-item">
            <template #prepend>
              <v-checkbox-btn
                :model-value="item.bought"
                :aria-label="`Marcar ${item.name} como comprado`"
                color="secondary"
                @update:model-value="(v: boolean | null) => marcar(item, v)"
              />
            </template>
            <v-list-item-title
              :class="{ 'text-decoration-line-through text-medium-emphasis': item.bought }"
              >{{ item.name }}</v-list-item-title
            >
            <v-list-item-subtitle v-if="item.quantity">{{ item.quantity }}</v-list-item-subtitle>
            <template #append>
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

      <v-btn
        v-if="shopping.comprados"
        block
        size="large"
        variant="tonal"
        color="error"
        prepend-icon="mdi-broom"
        @click="confirmandoLimpiar = true"
      >
        Eliminar comprados ({{ shopping.comprados }})
      </v-btn>
    </template>

    <ConfirmDialog
      v-model="confirmando"
      titulo="¿Quitar de la lista?"
      :texto="`Se eliminará «${porEliminar?.name ?? ''}» de tu lista de la compra.`"
      :cargando="eliminando"
      @confirmar="eliminar"
    />
    <ConfirmDialog
      v-model="confirmandoLimpiar"
      titulo="¿Eliminar los productos comprados?"
      texto="Se quitarán de la lista todos los que ya has marcado como comprados."
      confirmar="Eliminar"
      :cargando="limpiando"
      @confirmar="limpiar"
    />
  </v-container>
</template>
