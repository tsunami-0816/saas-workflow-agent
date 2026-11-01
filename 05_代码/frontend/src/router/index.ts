import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { TOKEN_KEY, USER_KEY } from '@/utils/env'
import type { Role } from '@/types'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login-view.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/main-layout.vue'),
    redirect: '/workflows',
    children: [
      {
        path: 'workflows',
        name: 'workflow-list',
        component: () => import('@/views/workflow-list-view.vue'),
        meta: { title: '流程管理' }
      },
      {
        path: 'workflows/:id/edit',
        name: 'workflow-editor',
        component: () => import('@/views/workflow-editor-view.vue'),
        // viewer 仅可查看画布（编辑器内按角色禁用保存/发布等写操作）
        meta: { title: '流程画布' }
      },
      {
        path: 'executions',
        name: 'execution-list',
        component: () => import('@/views/execution-list-view.vue'),
        meta: { title: '执行监控' }
      },
      {
        path: 'executions/:id',
        name: 'execution-detail',
        component: () => import('@/views/execution-detail-view.vue'),
        meta: { title: '执行详情' }
      },
      {
        path: 'mqtt-subscriptions',
        name: 'mqtt-subscription',
        component: () => import('@/views/mqtt-subscription-view.vue'),
        meta: { title: 'MQTT 订阅' }
      },
      {
        path: 'quota',
        name: 'quota',
        component: () => import('@/views/quota-view.vue'),
        meta: { title: '额度与计量' }
      },
      {
        path: 'audit-logs',
        name: 'audit-log',
        component: () => import('@/views/audit-log-view.vue'),
        meta: { title: '审计日志', roles: ['admin'] as Role[] }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/workflows' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/** 路由守卫：未登录跳登录；admin 专属页面对非 admin 拦截（FE-1.2 双保险前端半） */
router.beforeEach((to) => {
  const authed = !!localStorage.getItem(TOKEN_KEY)
  if (to.meta.public) {
    return isLoginRedirect(to.path, authed)
  }
  if (!authed) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  const needRoles = to.meta.roles as Role[] | undefined
  if (needRoles && needRoles.length > 0) {
    const role = readRole()
    if (!role || !needRoles.includes(role)) {
      ElMessage.warning('当前角色无权访问该页面')
      return { path: '/workflows' }
    }
  }
  return true
})

function isLoginRedirect(path: string, loggedIn: boolean) {
  if (path === '/login' && loggedIn) {
    return { path: '/workflows' }
  }
  return true
}

function readRole(): Role | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw).role as Role) : null
  } catch {
    return null
  }
}

export default router
