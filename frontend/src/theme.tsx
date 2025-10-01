import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react"
import { buttonRecipe } from "./theme/button.recipe"

const customConfig = defineConfig({
  disableLayers: true,
  globalCss: {
    html: {
      fontSize: "16px",
    },
    body: {
      fontSize: "0.875rem",
      margin: 0,
      padding: 0,
    },
    ".main-link": {
      color: "ui.main",
      fontWeight: "bold",
      textDecoration: "none",
      transition: "all 0.2s",
      _hover: {
        textDecoration: "underline",
      },
    },
    ".auth-button": {
      height: "48px",
      fontSize: "16px",
      fontWeight: "600",
      transition: "all 0.2s",
      _hover: {
        transform: "scale(1.02)",
        filter: "brightness(1.1)",
      },
    },
    ".auth-input": {
      height: "48px",
      fontSize: "16px",
      transition: "all 0.2s",
      _focus: {
        boxShadow: "0 0 0 3px rgba(99, 102, 241, 0.1)",
        borderColor: "#6366F1",
      },
    },
  },
  theme: {
    tokens: {
      colors: {
        ui: {
          main: { value: "#009688" },
        },
        brand: {
          primary: { value: "#6366F1" },
          primaryDark: { value: "#4F46E5" },
          secondary: { value: "#8B5CF6" },
          text: { value: "#1F2937" },
          textLight: { value: "#6B7280" },
          success: { value: "#10B981" },
          error: { value: "#EF4444" },
          warning: { value: "#F59E0B" },
        },
      },
    },
    recipes: {
      button: buttonRecipe,
    },
  },
})

export const system = createSystem(defaultConfig, customConfig)