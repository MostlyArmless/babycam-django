import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      // We're proxying the webcam stream using vite so that the browser doesn't throw a CORS error.
      // This is only required if the stream is authenticated,
      // you can get rid of this if you remove the username+password auth on the webcam server side.
      '/webcam': {
        target: 'http://192.168.0.222:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/webcam/, ""),
      },
    },
  },
})
