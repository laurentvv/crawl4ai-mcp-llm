import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

const rootDir = fileURLToPath(new URL('.', import.meta.url));
const outDir = resolve(rootDir, '../src/crawl4ai_mcp_llm/ui_assets');

const entries = ['crawl-card.html', 'explorer.html'];

for (const [index, entry] of entries.entries()) {
  await build({
    root: rootDir,
    plugins: [viteSingleFile()],
    build: {
      outDir,
      emptyOutDir: index === 0,
      target: 'es2022',
      assetsInlineLimit: 100_000_000,
      cssCodeSplit: false,
      rollupOptions: {
        input: resolve(rootDir, entry),
      },
    },
  });
}
