import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [preact()],

  // Base path for Home Assistant ingress support
  // This will be overridden at runtime if X-Ingress-Path is set
  base: '/',

  // Build optimizations
  build: {
    target: 'es2020',
    outDir: 'dist',
    assetsDir: 'assets',

    // Optimize bundle size - target <100KB gzipped
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },

    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['preact', 'preact-router'],
        },
      },
    },

    // Report compressed size
    reportCompressedSize: true,
    chunkSizeWarningLimit: 100,
  },

  // Development server config
  server: {
    port: 3000,
    strictPort: false,

    // Proxy API requests to Flask backend during development
    proxy: {
      '/api': {
        target: 'http://localhost:8099',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8099',
        ws: true,
      },
    },
  },

  // Preview server config
  preview: {
    port: 3000,
  },

  // Resolve aliases
  resolve: {
    alias: {
      'react': 'preact/compat',
      'react-dom': 'preact/compat',
    },
  },

  // Optimize dependencies
  optimizeDeps: {
    include: ['preact', 'preact-router'],
  },
});
