import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // A function form, not an object: object-form manualChunks is not
        // supported by every Vite 6+ build pipeline (rolldown-vite) and fails
        // the build outright rather than falling back.
        manualChunks(id: string) {
          if (id.includes("node_modules")) {
            if (id.includes("chart.js") || id.includes("react-chartjs-2")) return "charts";
            if (id.includes("@tanstack")) return "query";
            if (id.includes("react-router")) return "router";
            if (id.includes("/react/") || id.includes("/react-dom/")) return "vendor";
          }
          return undefined;
        },
      },
    },
  },
});
