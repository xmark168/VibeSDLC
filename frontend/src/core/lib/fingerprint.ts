import FingerprintJS from '@fingerprintjs/fingerprintjs'

/**
 * Cached fingerprint value to avoid recalculating
 * Fingerprint remains constant for the browser/device
 */
let cachedFingerprint: string | null = null

/**
 * Promise to track ongoing fingerprint generation
 * Prevents race conditions when multiple calls are made simultaneously
 */
let fingerprintPromise: Promise<string> | null = null

/**
 * Get a unique device fingerprint for security purposes
 * Uses FingerprintJS library to generate a consistent browser fingerprint
 *
 * The fingerprint is cached after first calculation to improve performance
 * on subsequent calls. Includes mutex lock to prevent race conditions.
 *
 * @returns Promise resolving to a unique fingerprint string
 *
 * @example
 * ```ts
 * const fingerprint = await getDeviceFingerprint()
 * // Use fingerprint for security purposes
 * ```
 */
export const getDeviceFingerprint = async (): Promise<string> => {
  // Return cached value if available
  if (cachedFingerprint) {
    return cachedFingerprint
  }

  // If already generating, return the existing promise
  if (fingerprintPromise) {
    return fingerprintPromise
  }

  // Create new fingerprint generation promise
  fingerprintPromise = (async () => {
    try {
      // Load the FingerprintJS agent
      // We use requestIdleCallback to avoid impacting page performance
      const fpPromise = FingerprintJS.load()

      // Get the visitor identifier
      const fp = await fpPromise
      const result = await fp.get()

      // Cache and return the fingerprint
      cachedFingerprint = result.visitorId
      return cachedFingerprint
    } catch {
      // Fallback: generate a secure random ID if fingerprinting fails
      // This ensures the app continues to work even if fingerprinting is blocked

      // Use crypto.randomUUID() for secure random ID generation
      const fallbackId = crypto.randomUUID?.() ||
        `fallback-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

      cachedFingerprint = fallbackId
      return fallbackId
    } finally {
      // Clear the promise after completion
      fingerprintPromise = null
    }
  })()

  return fingerprintPromise
}
