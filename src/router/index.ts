import type { RouteRecordRaw } from 'vue-router'
import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardPage from '@/pages/dashboard/DashboardPage.vue'
import SettingsPage from '@/pages/settings/SettingsPage.vue'
import WorkspacePage from '@/pages/workspace/WorkspacePage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: DashboardPage,
    meta: { navKey: 'dashboard' }
  },
  {
    path: '/project/:id',
    redirect: (to) => ({
      name: 'project-chat',
      params: to.params
    })
  },
  {
    path: '/project/:id/chat',
    name: 'project-chat',
    component: WorkspacePage,
    props: (route) => ({
      projectId: String(route.params.id),
      mode: 'chat' as const
    }),
    meta: { navKey: 'project' }
  },
  {
    path: '/project/:id/preview',
    name: 'project-preview',
    component: WorkspacePage,
    props: (route) => ({
      projectId: String(route.params.id),
      mode: 'preview' as const
    }),
    meta: { navKey: 'project' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsPage,
    meta: { navKey: 'settings' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

export default router

