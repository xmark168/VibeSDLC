import { Box, HStack, Text } from "@chakra-ui/react"

interface DividerWithTextProps {
  text: string
}

export function DividerWithText({ text }: DividerWithTextProps) {
  return (
    <HStack className="w-full my-6">
      <Box className="flex-1 h-px bg-gray-200" />
      <Text fontSize="sm" color="#9CA3AF" px="4">
        {text}
      </Text>
      <Box className="flex-1 h-px bg-gray-200" />
    </HStack>
  )
}