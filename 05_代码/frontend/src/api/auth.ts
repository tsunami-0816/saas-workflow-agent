import request from './request'
import type { CurrentUser, LoginResponse } from '@/types'

/** 登录签发 JWT */
export function login(data: { username: string; password: string }) {
  return request.post<unknown, LoginResponse>('/auth/login', data)
}

/** 当前登录用户信息 */
export function me() {
  return request.get<unknown, CurrentUser>('/auth/me')
}
