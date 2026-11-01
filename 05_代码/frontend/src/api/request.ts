import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import type { Result } from '@/types'
import { TOKEN_KEY, USER_KEY, USE_MOCK } from '@/utils/env'
import { mockAdapter } from '@/mock'

/**
 * axios 封装（FE-1.1）：
 * - baseURL=/api/v1，请求头自动带 JWT；
 * - 统一响应壳 {code,message,data}：code=0 直接返回 data，其余统一错误提示；
 * - 网络失败/超时统一提示；HTTP 401 / code=10401 清会话跳登录；
 * - Mock 模式下走本地 mockAdapter（INF-3）。
 */
const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  adapter: USE_MOCK ? mockAdapter : undefined
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 清会话并跳登录（401 统一口径） */
function toLogin() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  if (!window.location.pathname.startsWith('/login')) {
    window.location.assign('/login')
  }
}

request.interceptors.response.use(
  (response: AxiosResponse<Result>) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        return body.data as never
      }
      if (body.code === 10401) {
        ElMessage.error(body.message || '登录已失效，请重新登录')
        toLogin()
        return Promise.reject(new Error(body.message))
      }
      if (body.code === 10403) {
        ElMessage.error(body.message || '越权访问：当前角色无权执行该操作')
        return Promise.reject(new Error(body.message))
      }
      if (body.code === 40429) {
        ElMessage.error(body.message || '租户额度不足，请联系管理员')
        return Promise.reject(new Error(body.message))
      }
      ElMessage.error(body.message || `请求失败（${body.code}）`)
      return Promise.reject(new Error(body.message))
    }
    return response.data as never
  },
  (error: AxiosError<Result>) => {
    if (error.response) {
      const status = error.response.status
      const body = error.response.data
      if (status === 401 || body?.code === 10401) {
        ElMessage.error(body?.message || '未登录或凭证已失效')
        toLogin()
      } else if (status === 403 || body?.code === 10403) {
        ElMessage.error(body?.message || '越权访问：当前角色无权执行该操作')
      } else if (status === 429 || body?.code === 40429) {
        ElMessage.error(body?.message || '租户额度不足，请联系管理员')
      } else {
        ElMessage.error(body?.message || `请求失败（HTTP ${status}）`)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络异常，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default request
