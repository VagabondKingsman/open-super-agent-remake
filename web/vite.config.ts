import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 构建产物放进 osa/static/dist，由 FastAPI 直接提供；开发时把接口代理到 8765
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../osa/static/dist',
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        // React lives in its own long-cached chunk so app edits do not invalidate it
        codeSplitting: { groups: [{ name: 'react-vendor', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/, priority: 10 }] },
      },
    },
  },
  server: { proxy: { '/api': 'http://127.0.0.1:8765', '/ws': { target: 'ws://127.0.0.1:8765', ws: true } } },
})
