import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 打包产物输出到 Python 后端目录下的 dist，方便 pywebview 直接加载
  build: {
    outDir: '../backend/dist',
    emptyOutDir: true,
  },
  // 使用相对路径，保证打包后在本地文件协议下也能正确加载资源
  base: './',
})
