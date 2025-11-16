# AI Agent Guidelines for React + Vite Frontend Development

---

## Tech Stack

- Runtime: Node.js 18+
- Build Tool: Vite 5.x
- Framework: React 18.x
- Language: TypeScript 5.x
- Routing: React Router v6
- State Management: Zustand / React Context
- HTTP Client: Axios
- UI Components: Tailwind CSS / shadcn/ui
- Form Handling: React Hook Form + Zod
- Testing: Vitest + React Testing Library

---

## Architecture Flow

```
Pages → Components → Hooks → Services → API Client
```

MANDATORY: Always follow this layered architecture. Each layer depends on the previous one.

---

## Folder Structure

```
src/
├── api/              # API client configuration (axios instance)
├── assets/           # Static assets (images, fonts, icons)
├── components/       # Reusable UI components
│   ├── common/       # Generic components (Button, Input, Modal)
│   ├── layout/       # Layout components (Header, Footer, Sidebar)
│   └── features/     # Feature-specific components
├── config/           # App configuration (env, constants)
├── constants/        # Application constants (routes, status codes)
├── hooks/            # Custom React hooks
├── pages/            # Page components (route components)
├── routes/           # Route definitions and guards
├── services/         # Business logic and API calls
├── stores/           # State management (Zustand stores / Context)
├── types/            # TypeScript type definitions
├── utils/            # Utility functions (formatters, validators, helpers)
└── tests/            # Test files
```

---

## Implementation Rules

### Rule 1: Implementation Order

MANDATORY SEQUENCE: Types → API Services → Hooks → Components → Pages → Routes → Tests

### Rule 2: Separation of Concerns

**Pages**: Route components, compose feature components. NO business logic.
**Components**: UI rendering, event handling, call hooks. NO API calls directly.
**Hooks**: State management, side effects, call services. NO UI rendering.
**Services**: API calls, data transformation. NO React-specific code.

### Rule 3: Naming Conventions

- PascalCase: `LoginPage.tsx`, `UserCard.tsx`, `Button.tsx` (components and pages)
- camelCase: `useAuth.ts`, `userService.ts`, `formatDate.ts` (hooks, services, utils)
- kebab-case: `LoginPage.test.tsx`, `useAuth.test.ts` (tests only)
- UPPER_SNAKE_CASE: `API_BASE_URL`, `MAX_FILE_SIZE` (constants)

## Setup Commands
- Install deps: `npm install`
- Start dev server: `npm run dev`
- Build for production: `npm run build`
- Preview production build: `npm run preview`
- Run tests: `npm test`
- Run linter: `npm run lint`

## Implementation Checklist

1. Define TypeScript types/interfaces
2. Create API service functions
3. Create custom hooks (if needed)
4. Create reusable components
5. Create page components
6. Define routes with guards
7. Write tests (components and hooks)
8. Add JSDoc/TSDoc comments

## Best Practices

### DO:
- Follow component composition pattern
- Use TypeScript for type safety
- Validate forms with Zod schemas
- Use custom hooks for reusable logic
- Implement error boundaries
- Use React.memo for expensive components
- Handle loading and error states
- Write accessible components (ARIA)
- Use environment variables for config
- Implement proper routing guards
- Write unit tests for hooks and components

### DON'T:
- Mix business logic in components
- Make API calls directly in components
- Skip TypeScript types (use `any`)
- Mutate state directly
- Use inline styles (use Tailwind classes)
- Skip error handling
- Hardcode API URLs or sensitive data
- Use console.log in production (use proper logging)
- Skip accessibility attributes
- Forget to cleanup effects (useEffect return)
- Prop drill excessively (use context/state management)

## Accessibility Guidelines

- Use semantic HTML elements
- Add ARIA labels and roles
- Ensure keyboard navigation
- Maintain proper heading hierarchy
- Provide alt text for images
- Use sufficient color contrast
- Support screen readers
- Handle focus management