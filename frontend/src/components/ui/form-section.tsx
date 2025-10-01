import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormSectionProps {
  children: ReactNode
}

export function FormSection({ children }: FormSectionProps) {
  return (
    <Box className="w-full">
      {children}
    </Box>
  )
}