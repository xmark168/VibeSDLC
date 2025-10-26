# VibeSDLC Frontend - Project Context

## Project Overview

This is a modern React frontend application built for the VibeSDLC project with TypeScript, Vite, and Chakra UI. The application follows modern development practices with file-based routing, server state management, and comprehensive tooling for development, testing, and deployment.

**Key Characteristics:**
- Built with React 19 and TypeScript 5
- Uses Vite 7 as the build tool and development server
- Implements TanStack Router for file-based routing
- Uses TanStack Query for server state management and caching
- Styled with Chakra UI v3 and Emotion for CSS-in-JS
- Linted and formatted with Biome (replaces ESLint + Prettier)
- E2E tested with Playwright

## Architecture

### Core Technologies
- **Framework**: React 19 with TypeScript 5
- **Build Tool**: Vite 7 with SWC plugin
- **Routing**: TanStack Router with file-based routing
- **State Management**: TanStack Query for server state, React hooks for local state
- **UI Library**: Chakra UI v3 with custom components
- **Forms**: React Hook Form with Zod validation
- **HTTP Client**: Axios with auto-generated API client from OpenAPI specs

### Project Structure
```
src/
├── client/              # Auto-generated API client from OpenAPI
├── components/          # React components organized by feature
│   ├── auth/           # Authentication components
│   ├── chat/           # Chat feature components  
│   ├── landing/        # Landing page components
│   ├── provider/       # Context providers
│   ├── shared/         # Shared/reusable components
│   └── ui/             # UI primitives and Chakra UI wrappers
├── apis/               # API service definitions
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries and helpers
├── queries/            # TanStack Query hooks and configuration
├── routes/             # File-based routing (TanStack Router)
├── types/              # TypeScript type definitions
├── utils.ts            # Global utility functions
└── main.tsx           # App entry point
```

### Key Files
- `main.tsx`: Application entry point with theme provider, query client, and router setup
- `routeTree.gen.ts`: Auto-generated route tree from TanStack Router
- `vite.config.ts`: Vite configuration with path aliases and code splitting
- `tsconfig.json`: TypeScript configuration with path mappings
- `biome.json`: Linting and formatting configuration

## Development Workflow

### Prerequisites
- **Node.js** >= 24.0.0
- **npm** >= 10.0.0

### Installation
1. Install dependencies: `npm install`
2. Set up environment variables: `cp .env.example .env` and edit with your backend API URL
3. Start development server: `npm run dev`

### Available Scripts
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

### Development Conventions
- Use file-based routing with TanStack Router in `src/routes/`
- Follow existing component patterns in `src/components/`
- Use TypeScript interfaces for props
- Use custom hooks from `src/hooks/` for common functionality
- API calls are made through the auto-generated client from OpenAPI specs
- All routes are automatically code-split
- Use the `@` alias for importing from `src/`
- Use the `@client` alias for importing from `src/client/`

### Path Aliases
- `@` maps to `src/`
- `@client` maps to `src/client/`

### API Integration
The API client is auto-generated from OpenAPI specs and located in `src/client/`. The client is configured in `@client/setup` which handles authentication tokens and base URLs from environment variables. API calls should be made through the services in the client, often combined with TanStack Query hooks for caching and state management.

## Key Development Patterns

### Routing
- Routes are automatically generated from files in `src/routes/`
- Use `_layout.tsx` for nested layouts
- Protected routes use authentication guards
- Route components are automatically code-split for performance

### State Management
- TanStack Query for server state (data fetching, mutations)
- React state (useState, useReducer) for local UI state
- Authentication state is managed in custom hooks
- Global state patterns use React Context providers

### Styling
- Chakra UI components with custom theme in `src/components/provider/theme-provider`
- Use the theme configuration for consistent styling
- CSS-in-JS with Emotion for complex styling needs
- Tailwind CSS for utility classes (if configured)

### Forms
- React Hook Form for form handling
- Zod for validation schemas
- Custom form components in `src/components/ui/` for consistent UX

### Testing
- E2E tests with Playwright in the `tests/` directory
- Type checking with TypeScript strict mode
- Linting with Biome for consistent code style
- The `npm run ci` command runs all checks: typecheck + lint + build

## Environment Variables
The application uses the VITE prefix for environment variables that get exposed to the client:
- `VITE_API_URL`: The backend API URL (defaults to http://localhost:8000)

## Code Quality Tools
- **Biome**: Handles both linting and formatting with opinionated rules
- **TypeScript**: Strict mode with comprehensive type checking
- **React Hook Form + Zod**: For form validation and type safety
- The development environment should be configured to format code on save using Biome

## Common Issues and Solutions
- Build warnings: Avoid named exports from route files, keep route components minimal
- Type errors: Run `npm run typecheck`, regenerate API client if backend changes
- Linting issues: Run `npm run lint` to auto-fix most issues
- Performance: Routes are automatically code-split, use dynamic imports for large components
- Authentication: API errors with status 401/403 trigger automatic logout and redirect to login

## Security Considerations
- API authentication tokens are stored in localStorage
- Authenticated API requests include proper headers
- 401/403 responses trigger automatic logout to prevent unauthorized access
- Input validation is handled through Zod schemas with React Hook Form