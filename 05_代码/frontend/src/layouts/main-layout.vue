<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">SaaS 工作流平台</div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#a6adb4" active-text-color="#fff">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title || '' }}</span>
        <div class="user-box">
          <el-tag size="small" :type="roleTagType">{{ roleText }}</el-tag>
          <span class="username">{{ auth.user?.username }}</span>
          <el-button link type="primary" @click="onLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

/** 菜单按角色过滤（FE-1.2 双保险前端半）：审计日志仅 admin 可见 */
const allMenus: { path: string; title: string; roles: Role[] }[] = [
  { path: '/workflows', title: '流程管理', roles: ['admin', 'dev', 'viewer'] },
  { path: '/executions', title: '执行监控', roles: ['admin', 'dev', 'viewer'] },
  { path: '/mqtt-subscriptions', title: 'MQTT 订阅', roles: ['admin', 'dev', 'viewer'] },
  { path: '/quota', title: '额度与计量', roles: ['admin', 'dev', 'viewer'] },
  { path: '/audit-logs', title: '审计日志', roles: ['admin'] }
]

const menus = computed(() => allMenus.filter((m) => auth.role && m.roles.includes(auth.role)))

const activeMenu = computed(() => {
  if (route.path.startsWith('/executions')) return '/executions'
  if (route.path.startsWith('/workflows')) return '/workflows'
  return route.path
})

const roleText = computed(() => ({ admin: '管理员', dev: '开发者', viewer: '只读' })[auth.role || 'viewer'])
const roleTagType = computed<'danger' | 'primary' | 'info'>(() => (auth.role === 'admin' ? 'danger' : auth.role === 'dev' ? 'primary' : 'info'))

async function onLogout() {
  await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #001529; }
.logo { color: #fff; font-size: 16px; font-weight: 600; padding: 18px 16px; }
.aside :deep(.el-menu) { border-right: none; }
.header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e4e7ed; background: #fff; }
.page-title { font-weight: 600; }
.user-box { display: flex; align-items: center; gap: 10px; }
.username { color: #606266; }
.main { background: #f5f7fa; padding: 0; overflow: auto; }
</style>
