import { mount, type ComponentMountingOptions } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { Component } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'

const Vacia = { template: '<div />' }

/** Monta un componente con Vuetify, Pinia y un router en memoria con las rutas de la app. */
export async function montar(
  componente: Component,
  opciones: ComponentMountingOptions<unknown> = {},
) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Vacia },
      { path: '/login', name: 'login', component: Vacia },
      { path: '/register', name: 'register', component: Vacia },
      { path: '/recipes/:externalId', name: 'recipe', component: Vacia },
    ],
  })
  await router.push('/login')
  await router.isReady()
  const wrapper = mount(
    componente as never,
    {
      ...(opciones as object),
      global: { ...opciones.global, plugins: [createVuetify(), pinia, router] },
    } as never,
  )
  return { wrapper, router, pinia }
}
