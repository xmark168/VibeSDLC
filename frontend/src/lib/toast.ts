import hotToast from "react-hot-toast"

export const toast = {
  success: (
    message: string,
    options?: Parameters<typeof hotToast.success>[1],
  ) => hotToast.success(message, options),
  error: (message: string, options?: Parameters<typeof hotToast.error>[1]) =>
    hotToast.error(message, options),
  loading: (
    message: string,
    options?: Parameters<typeof hotToast.loading>[1],
  ) => hotToast.loading(message, options),
  dismiss: (toastId?: string) => hotToast.dismiss(toastId),
  promise: hotToast.promise,
  // Compatibility methods (sonner-like API)
  info: (message: string, options?: Parameters<typeof hotToast>[1]) =>
    hotToast(message, { icon: "ℹ️", ...options }),
  warning: (message: string, options?: Parameters<typeof hotToast>[1]) =>
    hotToast(message, { icon: "⚠️", ...options }),
}

export default toast
export { hotToast }
