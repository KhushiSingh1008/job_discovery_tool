import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin API calls in development: no CORS, no hard-coded host in the app.
    proxy: { "/api": { target: API_TARGET, changeOrigin: true } },
  },
  // three.js is not chunked by hand: the scenes are loaded with React.lazy, so the
  // bundler already puts it in async chunks fetched only when a 3D scene renders.
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
    restoreMocks: true,
  },
});
