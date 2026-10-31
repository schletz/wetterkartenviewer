import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Relative paths: GitHub Pages serves the app below /wetterkartenviewer/.
  base: './',
  server: {
    // data/ and maps/ are rewritten by scripts/update_maps.py; reloading on every write would be useless.
    watch: { ignored: ['**/data/**', '**/maps/**'] },
  },
})
