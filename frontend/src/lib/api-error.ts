/**
 * Parse API error response to user-friendly message
 * Handles FastAPI 422 validation errors and standard error formats
 */
export function parseApiError(error: any): string {
  // FastAPI 422 validation error format: { detail: [{ loc: [...], msg: "...", type: "..." }] }
  if (error?.body?.detail && Array.isArray(error.body.detail)) {
    const messages = error.body.detail.map((err: any) => {
      const field = err.loc?.slice(1).join(".") || "field"
      return `${field}: ${err.msg}`
    })
    return messages.length > 0 ? messages.join("; ") : "Validation failed"
  }

  // Standard string detail format
  if (error?.body?.detail && typeof error.body.detail === "string") {
    return error.body.detail
  }

  // Direct message property
  if (error?.message) {
    return error.message
  }

  return "An unexpected error occurred"
}
