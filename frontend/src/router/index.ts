import { createRouter, createWebHistory } from 'vue-router'
import VistaProvisional from '@/views/VistaProvisional.vue'

declare module 'vue-router' {
  interface RouteMeta {
    titulo?: string
  }
}

/** Rutas definidas desde el principio; cada pantalla real llega en su fase. */
export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: VistaProvisional,
      meta: { titulo: 'Iniciar sesión' },
    },
    {
      path: '/register',
      name: 'register',
      component: VistaProvisional,
      meta: { titulo: 'Crear cuenta' },
    },
    { path: '/', name: 'home', component: VistaProvisional, meta: { titulo: '¿Qué cocino hoy?' } },
    { path: '/pantry', name: 'pantry', component: VistaProvisional, meta: { titulo: 'Despensa' } },
    {
      path: '/shopping-list',
      name: 'shopping-list',
      component: VistaProvisional,
      meta: { titulo: 'Lista de la compra' },
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: VistaProvisional,
      meta: { titulo: 'Favoritos' },
    },
    {
      path: '/recipes/:externalId',
      name: 'recipe',
      component: VistaProvisional,
      meta: { titulo: 'Receta' },
    },
  ],
})
