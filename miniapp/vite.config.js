import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const cloudflareIgnorePlugin = () => {
  return {
    name: 'cloudflare-ignore',
    transformIndexHtml(html) {
      return html.replace(/<script /g, '<script data-cfasync="false" ');
    }
  }
}

export default defineConfig({
  plugins: [react(), cloudflareIgnorePlugin()],
  base: './',
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    css: true,
  },
});
