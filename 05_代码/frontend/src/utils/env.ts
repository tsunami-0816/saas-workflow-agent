/** 是否启用本地 Mock 层（INF-3）：仅由环境变量控制，切真实后端改 .env 即可 */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

/** localStorage 键 */
export const TOKEN_KEY = 'swa_token'
export const USER_KEY = 'swa_user'
