import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface AuthCardProps {
  children: ReactNode
}

export function AuthCard({ children }: AuthCardProps) {
  return (
    <Box
      className="w-full max-w-[450px] mx-auto"
      bg="white"
      borderRadius="12px"
      boxShadow="0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
      p="40px"
    >
      {children}
    </Box>
  )
}