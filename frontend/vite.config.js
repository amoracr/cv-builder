import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // Carga las variables de entorno basadas en el directorio actual
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/styles/variables" as *;`
        }
      }
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT || env.FRONTEND_PORT || 5173)
    }
  }
})