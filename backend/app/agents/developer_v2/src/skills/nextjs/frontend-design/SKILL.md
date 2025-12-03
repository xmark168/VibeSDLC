---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces. Use when implementing UI components, pages, or layouts.
---

# Frontend Design Guidelines

## Design Thinking (Before Coding)

1. **Purpose**: What problem does this interface solve?
2. **Tone**: Pick a direction - minimal, playful, editorial, luxury, brutalist...
3. **Differentiation**: What makes this UNFORGETTABLE?

## Typography

✅ DO:
- Distinctive fonts (Geist, Satoshi, Cabinet Grotesk, Outfit)
- Pair display font + body font
- Varied font weights

❌ AVOID:
- Generic fonts (Arial, Inter, Roboto)
- System fonts without styling

## Color & Theme

✅ DO:
- CSS variables for consistency
- Dominant color + sharp accents
- Dark/light theme support

❌ AVOID:
- Purple gradients on white (AI slop)
- Timid, evenly-distributed palettes

## Motion & Animation

✅ DO:
- Staggered reveals on page load
- Hover states that surprise
- CSS transitions for simple effects
- Framer Motion for complex animations

❌ AVOID:
- Scattered micro-interactions
- Animation without purpose

## Layout

✅ DO:
- Asymmetry, overlap, diagonal flow
- Grid-breaking elements
- Generous negative space

❌ AVOID:
- Everything centered
- Uniform rounded corners
- Cookie-cutter layouts

## Background & Details

✅ DO:
- Gradient meshes, noise textures
- Layered transparencies
- Subtle shadows and depth

❌ AVOID:
- Flat solid backgrounds
- No visual texture

## Quick Checklist

Before finishing UI work:
- [ ] Font is NOT Inter/Arial/Roboto
- [ ] Color scheme is NOT purple gradient
- [ ] Layout has some asymmetry
- [ ] Has at least one surprise element
- [ ] Matches the app's tone/purpose
