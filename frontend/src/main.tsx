import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ApiError } from "./client"
import "@/config/setup"
import { routeTree } from "./routeTree.gen"

import "./index.css"
import "./assets/fonts/ibm-plex-sans.regular.ttf"
import { Toaster } from "react-hot-toast"
import AuthProvider from "./components/provider/auth-provider"
import { ThemeProvider } from "./components/provider/theme-provider"

// OpenAPI is configured in @client/setup

const handleApiError = (error: Error) => {
  if (error instanceof ApiError && [401].includes(error.status)) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
          <Toaster
            position="top-center"
            toastOptions={{
              style: {
                maxWidth: '500px',
              },
              duration: 3000,
            }}
            containerStyle={{
              top: 20,
            }}
          />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
