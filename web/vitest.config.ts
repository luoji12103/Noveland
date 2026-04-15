import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const currentDirectory = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": currentDirectory,
    },
  },
  test: {
    environment: "jsdom",
    exclude: ["tests/e2e/**", "node_modules/**", ".next/**"],
    globals: true,
    include: ["**/*.test.ts", "**/*.test.tsx"],
    setupFiles: resolve(currentDirectory, "vitest.setup.ts"),
  },
});
