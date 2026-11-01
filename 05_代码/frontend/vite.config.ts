import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5177,
    host: true, // 监听 0.0.0.0，避免 Windows 下 localhost 仅解析为 IPv6 ::1 导致浏览器连不上
    proxy: {
      // 真实后端 java-backend
      '/api': {
        target: 'http://localhost:8083',
        changeOrigin: true
      }
    }
  }
})
