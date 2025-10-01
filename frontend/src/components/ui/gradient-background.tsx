import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface GradientBackgroundProps {
  children: ReactNode
}

export function GradientBackground({ children }: GradientBackgroundProps) {
  return (
    <Box
      className="min-h-screen w-full flex items-center justify-center p-5"
      bgGradient="to-br"
      gradientFrom="#F9FAFB"
      gradientTo="#EEF2FF"
    >
      {children}
    </Box>
  )
}