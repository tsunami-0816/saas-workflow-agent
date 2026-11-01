/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 是否启用本地 Mock 层（'true'/'false'） */
  readonly VITE_USE_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
