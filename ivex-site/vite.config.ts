import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import { THEME_SCRIPT, fillPlaceholders } from "./src/site/layout";
import { generatedPages } from "./src/site/pages";

const root = import.meta.dirname;

// Service and contact pages are rendered from src/site and written next to the
// hand-written pages (git-ignored), so Vite treats them as ordinary entries.
const generated = generatedPages();
for (const { file, html } of generated) {
  const path = resolve(root, file);
  if (existsSync(path) && readFileSync(path, "utf8") === html) continue;
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, html);
}

// Shared menu, footer, service list and form for the hand-written pages, and the
// theme switch every page needs before first paint.
const layout = (): Plugin => ({
  name: "ivx-layout",
  transformIndexHtml: {
    order: "pre",
    handler: (html) => ({ html: fillPlaceholders(html), tags: [{ tag: "script", children: THEME_SCRIPT, injectTo: "head-prepend" }] }),
  },
});

const pages = ["index.html", "hakkimizda/index.html", ...generated.map((p) => p.file)];

export default defineConfig({
  plugins: [layout()],
  build: {
    rollupOptions: {
      input: Object.fromEntries(pages.map((file) => [file.replace(/\/?index\.html$/, "") || "main", resolve(root, file)])),
    },
  },
});
