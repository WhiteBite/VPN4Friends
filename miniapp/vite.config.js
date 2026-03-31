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
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    css: true,
  },
});
