# VibeSDLC Frontend

A modern React frontend application built with TypeScript, Vite, and Chakra UI.

## 🚀 Quick Start

### Prerequisites

- **Node.js** >= 24.0.0 (check with `node --version`)
- **npm** >= 10.0.0 (check with `npm --version`)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd VibeSDLC/frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your backend API URL
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

   App will be available at: http://localhost:5173

## 🛠️ Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run linter (Biome) |
| `npm run typecheck` | Type checking with TypeScript |
| `npm run test:e2e` | Run E2E tests |
| `npm run test:e2e:ui` | Run E2E tests with UI |
| `npm run generate-client` | Generate API client from OpenAPI |
| `npm run ci` | Run all checks (typecheck + lint + build) |

## 📁 Project Structure

```
src/
├── client/              # Auto-generated API client
├── components/          # React components
│   ├── Admin/          # Admin management components
│   ├── Common/         # Shared/reusable components
│   ├── Items/          # Item management components
│   ├── ui/             # UI primitives (Chakra UI wrappers)
│   └── UserSettings/   # User settings components
├── hooks/              # Custom React hooks
├── routes/             # File-based routing (TanStack Router)
├── theme/              # Custom theme and styling
├── utils.ts            # Utility functions
└── main.tsx           # App entry point
```

## 🎨 Tech Stack

### Core
- **React 19** - UI framework
- **TypeScript 5** - Type safety
- **Vite 7** - Build tool & dev server

### Routing & State
- **TanStack Router** - Type-safe file-based routing
- **TanStack Query** - Server state management & caching

### UI & Styling
- **Chakra UI v3** - Component library
- **Emotion** - CSS-in-JS
- **React Icons** - Icon library

### Forms & HTTP
- **React Hook Form** - Form handling & validation
- **Axios** - HTTP client

### Development
- **Biome** - Linting & formatting (replaces ESLint + Prettier)
- **Playwright** - E2E testing
- **TypeScript** - Type checking

## 🔧 Development Workflow

### 1. **Adding New Pages**

Create a new route file in `src/routes/`:

```typescript
// src/routes/my-page.tsx
import { createFileRoute } from "@tanstack/react-router"

function MyPage() {
  return <div>My New Page</div>
}

export const Route = createFileRoute("/my-page")({
  component: MyPage,
})
```

### 2. **Creating Components**

Follow existing patterns in `src/components/`:

```typescript
// src/components/MyComponent.tsx
import { Box, Button } from "@chakra-ui/react"

interface MyComponentProps {
  title: string
}

function MyComponent({ title }: MyComponentProps) {
  return (
    <Box>
      <Button>{title}</Button>
    </Box>
  )
}

export default MyComponent
```

### 3. **Using Custom Hooks**

Check `src/hooks/` for existing hooks:

```typescript
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

function MyComponent() {
  const { user, logout } = useAuth()
  const { showSuccessToast } = useCustomToast()

  // Component logic...
}
```

### 4. **API Integration**

The API client is auto-generated from OpenAPI specs:

```typescript
import { UsersService, ItemsService } from "@/client"

// Use with TanStack Query
const { data: users } = useQuery({
  queryKey: ["users"],
  queryFn: UsersService.getUsers,
})
```

### 5. **Styling & Theming**

Custom styles go in `src/theme/`:

```typescript
// src/theme/my-component.recipe.ts
import { defineRecipe } from "@chakra-ui/react"

export const myComponentRecipe = defineRecipe({
  base: {
    padding: 4,
    borderRadius: "md",
  },
  variants: {
    size: {
      sm: { fontSize: "sm" },
      lg: { fontSize: "lg" },
    },
  },
})
```

## 🧪 Testing

### Running Tests

```bash
# E2E tests
npm run test:e2e

# E2E tests with UI
npm run test:e2e:ui

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Writing E2E Tests

Tests are in `tests/` directory using Playwright:

```typescript
// tests/my-feature.spec.ts
import { test, expect } from "@playwright/test"

test("should do something", async ({ page }) => {
  await page.goto("/my-page")
  await expect(page.getByText("My Page")).toBeVisible()
})
```

## 🔑 Environment Variables

Create `.env` file with:

```env
VITE_API_URL=http://localhost:8000
# Add other environment variables as needed
```

## 📚 Key Concepts

### File-based Routing
- Routes are automatically generated from files in `src/routes/`
- Use `_layout.tsx` for nested layouts
- Protected routes use `beforeLoad` guards

### Code Splitting
- Routes are automatically code-split
- Manual chunks are configured in `vite.config.ts`
- Keep components in route files minimal for better splitting

### State Management
- Use TanStack Query for server state
- Use React state (useState) for local UI state
- Authentication state is managed in `useAuth` hook

### Component Patterns
- Prefer function components over class components
- Use TypeScript interfaces for props
- Follow existing naming conventions

## 🚨 Common Issues

### Build Warnings
- Avoid named exports from route files
- Keep route components minimal
- Use dynamic imports for large components

### Type Errors
- Run `npm run typecheck` to catch issues early
- Regenerate API client if backend changes: `npm run generate-client`

### Linting Issues
- Run `npm run lint` to auto-fix most issues
- Biome is configured to format on save

## 🤝 Contributing

1. **Before starting:**
   ```bash
   npm run ci  # Ensure everything passes
   ```

2. **Development cycle:**
   - Make changes
   - Test locally: `npm run dev`
   - Run checks: `npm run ci`
   - Commit changes

3. **Code style:**
   - TypeScript strict mode is enabled
   - Use Biome for formatting (auto-runs on save)
   - Follow existing component patterns

## 📞 Getting Help

- **Documentation:** Check existing components for patterns
- **API:** Auto-generated client docs in `src/client/`
- **Issues:** Check build output for specific error messages
- **Debugging:** Use React DevTools and TanStack DevTools

---

**Happy coding! 🎉**