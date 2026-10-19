import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    titulo?: string
    /** Solo para usuarios con sesión. */
    privada?: boolean
    /** Solo para visitantes (login y registro). */
    soloInvitados?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { titulo: 'Iniciar sesión', soloInvitados: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { titulo: 'Crear cuenta', soloInvitados: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { titulo: '¿Qué cocino hoy?', privada: true },
    },
    {
      path: '/pantry',
      name: 'pantry',
      component: () => import('@/views/PantryView.vue'),
      meta: { titulo: 'Despensa', privada: true },
    },
    {
      path: '/shopping-list',
      name: 'shopping-list',
      component: () => import('@/views/ShoppingListView.vue'),
      meta: { titulo: 'Lista de la compra', privada: true },
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('@/views/FavoritesView.vue'),
      meta: { titulo: 'Favoritos', privada: true },
    },
    {
      path: '/recipes/:externalId',
      name: 'recipe',
      component: () => import('@/views/RecipeDetailView.vue'),
      meta: { titulo: 'Receta', privada: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.privada && !auth.autenticado) {
    return { name: 'login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  }
  if (to.meta.soloInvitados && auth.autenticado) return { name: 'home' }
})

router.afterEach((to) => {
  document.title = to.meta.titulo ? `${to.meta.titulo} · Recetario` : 'Recetario'
})

export default router
