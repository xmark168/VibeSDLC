import { Box, Heading, Text } from "@chakra-ui/react"

export function BrandingSection() {
  return (
    <Box className="flex flex-col h-full justify-between">
      {/* Logo */}
      <Box className="flex-shrink-0">
        <svg
          width="93"
          height="42"
          viewBox="0 0 93 42"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="21" cy="21" r="21" fill="black" />
          <text
            x="50"
            y="30"
            fontFamily="Arial, sans-serif"
            fontSize="28"
            fontWeight="bold"
            fill="black"
          >
            MGX
          </text>
        </svg>
      </Box>

      {/* Heading and Content */}
      <Box className="flex-1 flex flex-col justify-center min-h-0">
        <Heading
          size="3xl"
          className="mb-4"
          lineHeight="1.2"
          fontWeight="bold"
        >
          Dream, Chat, Create
          <br />
          Your{" "}
          <Text
            as="span"
            bgGradient="to-r"
            gradientFrom="#8B5CF6"
            gradientTo="#A78BFA"
            bgClip="text"
          >
            24/7 AI Team
          </Text>
        </Heading>

        <Text fontSize="md" color="#6B7280" className="mb-6">
          Providing the First AI Software Company
        </Text>

        {/* Character Image */}
        <Box className="flex justify-center items-center flex-1 min-h-0">
          <img
            src="/assets/images/charactor.png"
            alt="AI Team Characters"
            className="w-full h-full object-contain"
            style={{ maxHeight: "calc(100vh - 100px)", maxWidth: "100%" }}
          />
        </Box>
      </Box>
    </Box>
  )
}