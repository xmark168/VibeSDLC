import { Box, HStack, Text } from "@chakra-ui/react"
import { FiCheck } from "react-icons/fi"

interface PasswordRequirement {
  label: string
  met: boolean
}

interface PasswordRequirementsProps {
  requirements: PasswordRequirement[]
}

export function PasswordRequirements({
  requirements,
}: PasswordRequirementsProps) {
  return (
    <Box className="mt-3 space-y-2">
      {requirements.map((req, index) => (
        <HStack key={index} gap="2" className="items-center">
          <Box
            className="w-4 h-4 rounded-full flex items-center justify-center transition-all duration-200"
            bg={req.met ? "#10B981" : "#E5E7EB"}
          >
            {req.met && <FiCheck size={12} color="white" />}
          </Box>
          <Text
            fontSize="sm"
            color={req.met ? "#10B981" : "#6B7280"}
            className="transition-colors duration-200"
          >
            {req.label}
          </Text>
        </HStack>
      ))}
    </Box>
  )
}