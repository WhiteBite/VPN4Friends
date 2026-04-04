import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

const cloudflareIgnorePlugin = () => {
  return {
    name: 'cloudflare-ignore',
    transformIndexHtml(html) {
      return html.replace(/<script /g, '<script data-cfasync="false" ');
    }
  }
}

export default defineConfig({
  plugins: [
    ...preact().filter(p => !['preact:transform-hook-names'].includes(p.name)),
    cloudflareIgnorePlugin()
  ],
  base: './',
  build: {
    target: 'esnext',
    cssMinify: 'lightningcss',
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            return id.toString().split('node_modules/')[1].split('/')[0].toString();
          } else if (id.includes('src/')) {
            // Split components and pages aggressively
            return id.toString().split('/').pop().split('.')[0].toString();
          }
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    css: true,
  },
});
