import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // base './' = rutas relativas: requerido por Capacitor (APK Android/iOS)
  // y compatible con despliegue web en la raiz del dominio.
  base: './',
  plugins: [react(), tailwindcss()],
})
