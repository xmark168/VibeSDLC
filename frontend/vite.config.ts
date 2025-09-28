import path from "node:path"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vitejs.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React ecosystem
          react: ["react", "react-dom"],
          // UI library
          ui: ["@chakra-ui/react", "@emotion/react"],
          // TanStack libraries
          tanstack: [
            "@tanstack/react-query",
            "@tanstack/react-router",
            "@tanstack/react-query-devtools",
          ],
          // Icons and utils
          utils: ["react-icons", "axios", "react-hook-form"],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})
