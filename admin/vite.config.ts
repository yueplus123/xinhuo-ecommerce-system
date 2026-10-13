import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 管理后台：独立前端应用，部署在 /admin/ 下；接口走同域 /api（开发时由 Vite 代理到 Django）
export default defineConfig({
  base: '/admin/',
  plugins: [vue()],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  build: {
    target: 'es2015',
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-chunks': ['vue', 'vue-router', 'pinia'],
          'element-plus': ['element-plus']
        }
      }
    }
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001', changeOrigin: true },
      '/media': { target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001', changeOrigin: true }
    }
  }
})
