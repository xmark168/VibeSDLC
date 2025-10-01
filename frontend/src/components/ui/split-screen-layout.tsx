import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface SplitScreenLayoutProps {
  leftSide: ReactNode
  rightSide: ReactNode
}

export function SplitScreenLayout({
  leftSide,
  rightSide,
}: SplitScreenLayoutProps) {
  return (
    <Box className="flex h-screen overflow-hidden relative">
      {/* Smooth gradient background transition */}
      <Box
        className="absolute inset-0 pointer-events-none"
        bgGradient="to-r"
        gradientFrom="#E8E4F3"
        gradientTo="white"
        style={{
          background: "linear-gradient(to right, #E8E4F3 0%, #E8E4F3 45%, rgba(232, 228, 243, 0.5) 50%, white 55%, white 100%)",
        }}
      />

      {/* Left Side - Branding */}
      <Box
        className="hidden lg:flex lg:w-1/2 xl:w-3/5 relative z-10 overflow-hidden"
        p="40px"
      >
        {leftSide}
      </Box>

      {/* Right Side - Form */}
      <Box className="w-full lg:w-1/2 xl:w-2/5 flex items-center justify-center p-8 relative z-10 overflow-y-auto">
        <Box className="w-full max-w-md">{rightSide}</Box>
      </Box>
    </Box>
  )
}