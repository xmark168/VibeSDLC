import { defineRecipe } from "@chakra-ui/react"

export const buttonRecipe = defineRecipe({
  className: "button",
  base: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "semibold",
    borderRadius: "8px",
    transition: "all 0.2s",
    cursor: "pointer",
    _disabled: {
      opacity: 0.4,
      cursor: "not-allowed",
    },
  },
  variants: {
    variant: {
      solid: {
        bg: "colorPalette.solid",
        color: "colorPalette.contrast",
        _hover: {
          bg: "colorPalette.solid/90",
        },
      },
      black: {
        bg: "black",
        color: "white",
        _hover: {
          bg: "gray.800",
        },
      },
      outline: {
        borderWidth: "1px",
        borderColor: "colorPalette.solid",
        color: "colorPalette.solid",
        _hover: {
          bg: "colorPalette.subtle",
        },
      },
      ghost: {
        color: "colorPalette.solid",
        _hover: {
          bg: "colorPalette.subtle",
        },
      },
      subtle: {
        bg: "colorPalette.subtle",
        color: "colorPalette.fg",
        _hover: {
          bg: "colorPalette.muted",
        },
      },
      surface: {
        bg: "colorPalette.surface",
        color: "colorPalette.fg",
        shadow: "xs",
        _hover: {
          bg: "colorPalette.muted",
        },
      },
      plain: {
        color: "colorPalette.fg",
      },
    },
    size: {
      xs: {
        h: "8",
        minW: "8",
        textStyle: "xs",
        px: "3",
        gap: "2",
      },
      sm: {
        h: "9",
        minW: "9",
        textStyle: "sm",
        px: "3.5",
        gap: "2",
      },
      md: {
        h: "10",
        minW: "10",
        textStyle: "sm",
        px: "4",
        gap: "2",
      },
      lg: {
        h: "11",
        minW: "11",
        textStyle: "md",
        px: "4.5",
        gap: "2",
      },
      xl: {
        h: "12",
        minW: "12",
        textStyle: "md",
        px: "5",
        gap: "2",
      },
    },
  },
  defaultVariants: {
    variant: "solid",
    size: "md",
  },
})