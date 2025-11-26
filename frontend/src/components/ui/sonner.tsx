import { useTheme } from "@/components/provider/theme-provider"
import { Toaster as Sonner, ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: "bg-slate-800 border-slate-700 text-white",
          title: "text-white font-medium",
          description: "text-slate-300",
          success: "bg-slate-800 border-slate-700",
          error: "bg-slate-800 border-slate-700",
          loading: "bg-slate-800 border-slate-700",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
