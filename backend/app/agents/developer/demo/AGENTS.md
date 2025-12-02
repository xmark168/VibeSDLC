# AGENTS.md

## Project Overview

This is a Next.js 16 boilerplate project built with TypeScript, using App Router and fully integrated with modern tools:

- **Framework**: Next.js 16.0.3 with React 19.2.0
- **Styling**: Tailwind CSS 4 with shadcn/ui components
- **Database**: Prisma ORM with PostgreSQL
- **Form handling**: React Hook Form + Zod validation
- **State management**: Zustand
- **Testing**: Jest 30 with React Testing Library
- **UI Components**: Radix UI primitives with shadcn/ui
- **Icons**: Lucide React
- **Package manager**: bun

## Directory Structure

```
prisma/
    schema.prisma     # Prisma schema
    dev.db           # Development database
src/
    app/              # Next.js App Router pages and layouts
        api/         # API routes
        layout.tsx   # Root layout
        page.tsx     # Home page
    components/       # React components
        ui/          # shadcn/ui components (50+ components)
    hooks/           # Custom React hooks
    lib/             # Utility functions and helpers
        api-response.ts  # API response helpers
        utils.ts         # General utilities (cn function)
    services/        # Business logic and external services
    store/           # Zustand state management
    types/           # TypeScript type definitions
        api.types.ts # API response types
```
## Architecture Flow

```
Models -> Type -> API Routes -> Services -> Components -> Pages
```

MANDATORY: Always follow this layered architecture when building features. Each layer depends on the previous one.

### Coding Flow

When implementing a new feature, follow this exact order:

1. **Models** (`prisma/schema.prisma`) - Define database schema, run `npx prisma generate && npx prisma db push`
2. **Types** (`src/types/api.types.ts`) - Define API response types
3. **API Routes** (`app/api/[resource]/route.ts`) - Create GET/POST/PUT/DELETE handlers with Zod validation
4. **Services** (`src/services/`) - Extract complex business logic (optional)
5. **Components** (`src/components/`) - Build reusable UI components (add `'use client'` if interactive)
6. **Pages** (`app/[route]/page.tsx`) - Compose components, fetch data (Server Components by default)

### Key Principles

- Server Components by default, use `'use client'` only for interactivity
- Always validate API inputs with Zod
- Use Prisma-generated types everywhere
- Data flow: Server Component → Prisma → Client Component (via props)
- Mutations: Client Component → fetch API → Database → router.refresh()

## Setup Commands

```bash
# Install dependencies
bun install

# Run development server with Turbopack
bun dev

# Run development server with Webpack (fallback)
bun dev:webpack

# Build production
bun run build

# Start production server
bun start

# Lint code
bun lint

# Run tests
bun test

# Run tests in watch mode
bun test:watch

# Run tests with coverage
bun test:coverage
```

## Database Setup

```bash
# Generate Prisma Client
npx prisma generate

# Run migrations
npx prisma migrate dev

# Open Prisma Studio
npx prisma studio
```

## Code Style and Conventions

### TypeScript
- **Strict mode** is enabled in tsconfig.json
- Use `unknown` instead of `any` for type safety
- Target: ES2017
- Always define types explicitly, avoid implicit any

### Import Paths
- Use alias `@/*` for imports from `src/`
- Example: `import { Button } from '@/components/ui/button'`

### Component Patterns
- **Server Components** are the default (Next.js App Router)
- Add `"use client"` directive for Client Components
- Functional components with TypeScript
- Props interface should be clearly defined

### Styling
- Use Tailwind CSS utility classes
- Use `cn()` helper from `@/lib/utils` to merge classes
- shadcn/ui components are configured with "new-york" style
- CSS variables for theming

### API Routes
- Use type-safe API responses from `@/types/api.types.ts`
- Always use helper functions from `@/lib/api-response.ts`:
  - `successResponse()` for success responses
  - `errorResponse()` for error responses
  - `handleError()` for error handling
  - `handleZodError()` for validation errors
- Validate input with Zod schemas
- Use `ApiException` class for custom errors

### Form Handling
- Use React Hook Form with Zod resolver
- Validate schemas with Zod
- UI components from shadcn/ui form components

### State Management
- Zustand for global state
- React hooks for local state
- Server state should be managed via React Query (if needed)

## Testing Instructions

### Jest Setup
The project is configured with Jest 30 and React Testing Library:

- **Test framework**: Jest 30.2.0
- **Testing library**: @testing-library/react 16.3.0
- **Environment**: jsdom
- **TypeScript support**: ts-jest 29.4.5

### Running Tests

```bash
# Run all tests
bun test

# Run tests in watch mode (auto re-run on changes)
bun test:watch

# Run tests with coverage report
bun test:coverage
```

### Test File Conventions

- Place test files in `__tests__` folder or co-locate with the file being tested
- Naming convention: `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`
- Examples:
  - `src/components/ui/__tests__/button.test.tsx`
  - `src/lib/__tests__/utils.test.ts`
  - `src/components/MyComponent.test.tsx`

### Writing Tests

**Component tests:**
```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles user interactions', async () => {
    const user = userEvent.setup();
    const handleClick = jest.fn();

    render(<MyComponent onClick={handleClick} />);
    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

**Utility function tests:**
```typescript
import { myFunction } from './myFunction';

describe('myFunction', () => {
  it('returns expected result', () => {
    expect(myFunction('input')).toBe('expected output');
  });
});
```

### Test Best Practices

- Always write tests for new code
- Test both happy path and edge cases
- Use `describe` to group related tests
- Use descriptive test names
- Mock external dependencies (API calls, database, etc.)
- Aim for high coverage but focus on meaningful tests
- Test behavior, not implementation details

### Mocked Modules

Jest setup has pre-mocked:
- `next/navigation` (useRouter, usePathname, useSearchParams)
- `window.matchMedia`
- `IntersectionObserver`
- `ResizeObserver`

### Coverage Thresholds

Currently coverage thresholds are set at 0% to not block development. Should be increased gradually as codebase matures:

```typescript
// jest.config.ts
coverageThreshold: {
  global: {
    branches: 0,
    functions: 0,
    lines: 0,
    statements: 0,
  },
}
```

## Prisma Conventions

- Models should be defined in `prisma/schema.prisma`
- Use camelCase for field names
- Always run `prisma generate` after changing schema
- Migrations should have descriptive names

## Environment Variables

Create a `.env` file with the following variables:

```env
DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
NODE_ENV="development"
```

## Deployment

- Build with `bun run build`
- Deploy to Vercel (recommended) or any platform that supports Next.js
- Ensure environment variables are set correctly
- Database migrations should run before deploy

## Notes for AI Agents

- When creating new API routes, always use type-safe response helpers
- When creating forms, use React Hook Form + Zod
- When adding UI components, prioritize using existing shadcn/ui components
- When working with database, always update Prisma schema and run migrations
- Follow Next.js App Router conventions (Server Components by default)
- Avoid using `any` type - use `unknown` or define specific types
- Always write tests for new code and run `bun test` before committing
