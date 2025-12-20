'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'

export function URLSync() {
  const pathname = usePathname()

  useEffect(() => {
    // Listen for URL requests from parent window
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'REQUEST_URL') {
        // Send current URL back to parent
        event.source?.postMessage(
          {
            type: 'URL_UPDATE',
            url: window.location.href
          },
          { targetOrigin: event.origin }
        )
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  // Also send URL update when pathname changes (Next.js navigation)
  useEffect(() => {
    if (window.parent !== window) {
      // We're in an iframe, notify parent of URL change
      window.parent.postMessage(
        {
          type: 'URL_UPDATE',
          url: window.location.href
        },
        '*' // Parent will verify origin
      )
    }
  }, [pathname])

  return null
}
