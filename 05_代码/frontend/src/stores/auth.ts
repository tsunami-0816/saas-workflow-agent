import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { CurrentUser, Role } from '@/types'
import { TOKEN_KEY, USER_KEY } from '@/utils/env'

/** 可写角色（admin/dev）：流程/执行/MQTT 等写入口按此隐藏（viewer 只读） */
const WRITE_ROLES: Role[] = ['admin', 'dev']

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<CurrentUser | null>(readUser())

  function readUser(): CurrentUser | null {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? (JSON.parse(raw) as CurrentUser) : null
    } catch {
      return null
    }
  }

  const isLogin = computed(() => !!token.value)
  const role = computed<Role | null>(() => user.value?.role ?? null)
  /** 是否具备写权限（admin/dev） */
  const canWrite = computed(() => !!user.value && WRITE_ROLES.includes(user.value.role))
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setSession(newToken: string, newUser: CurrentUser) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLogin, role, canWrite, isAdmin, setSession, logout }
})
