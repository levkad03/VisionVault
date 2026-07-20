import { useAuthStore } from '@/stores/auth';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/pages/RegisterPage.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('@/pages/DashboardPage.vue') },
        { path: 'upload', name: 'upload', component: () => import('@/pages/UploadPage.vue') },
        { path: 'gallery', name: 'gallery', component: () => import('@/pages/GalleryPage.vue') },
        { path: 'search', name: 'search', component: () => import('@/pages/SearchPage.vue') },
      ],
    },
  ],
});

let hydrated = false;

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (!hydrated) {
    await auth.hydrate();
    hydrated = true;
  }

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }
  if (to.meta.public && auth.isAuthenticated) {
    return { name: 'dashboard' };
  }
});

export default router;
