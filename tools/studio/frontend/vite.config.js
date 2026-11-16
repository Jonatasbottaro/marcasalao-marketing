import { defineConfig } from 'vite';

export default defineConfig({
  base: '/static/frontend/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: 'src/main.jsx',
    },
  },
});
