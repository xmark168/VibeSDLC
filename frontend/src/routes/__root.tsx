import { createRootRoute, Outlet } from "@tanstack/react-router"
import React, { Suspense } from "react"

const loadDevtools = () =>
  Promise.all([
    import("@tanstack/router-devtools"),
    import("@tanstack/react-query-devtools"),
  ]).then(([routerDevtools, reactQueryDevtools]) => {
    return {
      default: () => (
        <>
          <routerDevtools.TanStackRouterDevtools />
          <reactQueryDevtools.ReactQueryDevtools />
        </>
      ),
    }
  })

const TanStackDevtools =
  process.env.NODE_ENV === "production" ? () => null : React.lazy(loadDevtools)

export const Route = createRootRoute({
  component: () => (
    <>
      <div style={{ fontFamily: "IBM Plex Sans" }}
      >
        <Outlet />
      </div>
      <Suspense>
        <TanStackDevtools />
      </Suspense>
    </>
  ),
  notFoundComponent: () => <div>Not Found</div>,
})
