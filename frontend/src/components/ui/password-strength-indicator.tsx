import { Box, HStack, Text } from "@chakra-ui/react"

interface PasswordStrengthIndicatorProps {
  strength: number // 0-4
}

export function PasswordStrengthIndicator({
  strength,
}: PasswordStrengthIndicatorProps) {
  const getColor = () => {
    if (strength <= 1) return "#EF4444" // red
    if (strength === 2) return "#F59E0B" // yellow/orange
    if (strength === 3) return "#10B981" // green
    return "#10B981" // strong green
  }

  const getLabel = () => {
    if (strength === 0) return ""
    if (strength <= 1) return "Weak"
    if (strength === 2) return "Fair"
    if (strength === 3) return "Good"
    return "Strong"
  }

  return (
    <Box className="w-full mt-2">
      <HStack gap="2" className="mb-1">
        {[1, 2, 3, 4].map((level) => (
          <Box
            key={level}
            className="h-1 flex-1 rounded-sm transition-all duration-300"
            bg={level <= strength ? getColor() : "#E5E7EB"}
          />
        ))}
      </HStack>
      {strength > 0 && (
        <Text fontSize="xs" color={getColor()} className="mt-1">
          {getLabel()}
        </Text>
      )}
    </Box>
  )
}