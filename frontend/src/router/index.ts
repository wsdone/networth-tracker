import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/reports',
      name: 'Reports',
      component: () => import('@/views/Reports.vue'),
    },
    {
      path: '/accounts',
      name: 'Accounts',
      component: () => import('@/views/Accounts.vue'),
    },
    {
      path: '/holdings',
      name: 'Holdings',
      component: () => import('@/views/Holdings.vue'),
    },
    {
      path: '/liabilities',
      name: 'Liabilities',
      component: () => import('@/views/Liabilities.vue'),
    },
    {
      path: '/expenses',
      name: 'Expenses',
      component: () => import('@/views/Expenses.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
    },
  ],
})

export default router
