import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The embeddable estimate: one self-contained script (styles inlined) at dist/widget/quick.js.
export default defineConfig({
  plugins: [react()],
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: 'dist/widget',
    emptyOutDir: true,
    lib: {
      entry: 'src/estimate/widget.tsx',
      name: 'PLDSolarEstimate',
      formats: ['iife'],
      fileName: () => 'quick.js',
    },
    cssCodeSplit: false,
  },
})
