# AGENTS.md - React + Vite Boilerplate

**AI Agent Guidelines for React + Vite + TypeScript Development**

---

## 🎯 Tech Stack

- **Runtime**: Node.js 18+
- **Framework**: React 18.2+ (Functional Components + Hooks)
- **Build Tool**: Vite 5.x
- **Language**: TypeScript 5.2+
- **Routing**: React Router DOM v6
- **State Management**: Zustand 4.x
- **Data Fetching**: React Query 3.x + Axios
- **Forms**: React Hook Form 7.x
- **Styling**: Tailwind CSS 3.x
- **UI Components**: Lucide React (icons)
- **Testing**: Vitest + React Testing Library
- **Code Quality**: ESLint + Prettier + TypeScript

---

## 🏗️ CRITICAL: Component Architecture

**MANDATORY PATTERN**: Functional Components + Hooks + TypeScript

```
┌─────────────────────────────────────────────────┐
│  Pages (Route Components)                       │
│  - Top-level route components                   │
│  - Compose multiple components                  │
│  - Handle page-level state                      │
│  - Connect to stores/queries                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Components (Reusable UI)                       │
│  - Presentational components                    │
│  - Accept props with TypeScript types           │
│  - Use custom hooks for logic                   │
│  - Export named components                      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Hooks (Custom Logic)                           │
│  - Reusable stateful logic                      │
│  - Prefix with 'use'                            │
│  - Return typed values                          │
│  - Follow React hooks rules                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Services (API Layer)                           │
│  - Axios instances                              │
│  - API endpoint functions                       │
│  - Request/response interceptors                │
│  - Type-safe API calls                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Stores (Global State)                          │
│  - Zustand stores                               │
│  - Typed state and actions                      │
│  - Persist middleware (if needed)               │
└─────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
src/
├── api-request/           # API request configurations
│   └── axios.ts           # Axios instance setup
├── components/            # Reusable UI components
│   ├── common/            # Common components (Button, Input, etc.)
│   ├── layout/            # Layout components (Header, Footer, etc.)
│   └── features/          # Feature-specific components
├── hooks/                 # Custom React hooks
│   ├── useAuth.ts         # Authentication hook
│   ├── useDebounce.ts     # Utility hooks
│   └── ...
├── pages/                 # Page components (routes)
│   ├── Home.tsx
│   ├── Login.tsx
│   └── ...
├── routes/                # Routing configuration
│   ├── index.tsx          # Main router setup
│   └── ProtectedRoute.tsx # Route guards
├── service/               # API service layer
│   ├── authService.ts
│   ├── userService.ts
│   └── ...
├── stores/                # Zustand stores
│   ├── authStore.ts
│   └── ...
├── types/                 # TypeScript type definitions
│   ├── api.types.ts
│   ├── user.types.ts
│   └── ...
├── utils/                 # Utility functions
│   ├── formatters.ts
│   ├── validators.ts
│   └── ...
├── App.tsx                # Root component
└── main.tsx               # Application entry point
```

---

## 🎯 CRITICAL IMPLEMENTATION RULES

### Rule #1: ALWAYS Use TypeScript

**MANDATORY**: All files must use TypeScript (.tsx for components, .ts for utilities)

```typescript
// ✅ CORRECT - Typed props
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({ label, onClick, variant = 'primary', disabled = false }) => {
  return (
    <button onClick={onClick} disabled={disabled} className={`btn-${variant}`}>
      {label}
    </button>
  );
};

// ❌ WRONG - No types
export const Button = ({ label, onClick, variant, disabled }) => {
  return <button onClick={onClick}>{label}</button>;
};
```

### Rule #2: NEVER Use Class Components

**MANDATORY**: Use functional components with hooks only

```typescript
// ✅ CORRECT - Functional component with hooks
import { useState, useEffect } from 'react';

export const UserProfile: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetchUser().then(setUser);
  }, []);

  return <div>{user?.name}</div>;
};

// ❌ WRONG - Class component
class UserProfile extends React.Component {
  state = { user: null };

  componentDidMount() {
    fetchUser().then(user => this.setState({ user }));
  }

  render() {
    return <div>{this.state.user?.name}</div>;
  }
}
```

### Rule #3: File Naming Conventions

- **PascalCase**: `UserProfile.tsx`, `LoginPage.tsx` (components/pages)
- **camelCase**: `authService.ts`, `useAuth.ts`, `formatDate.ts` (services/hooks/utils)
- **kebab-case**: `user-profile.test.tsx` (test files only)

### Rule #4: Path Aliases

**ALWAYS** use configured path aliases from `vite.config.ts`:

```typescript
// ✅ CORRECT - Use path aliases
import { Button } from '@components/common/Button';
import { useAuth } from '@hooks/useAuth';
import { authService } from '@services/authService';
import { User } from '@types/user.types';

// ❌ WRONG - Relative paths
import { Button } from '../../../components/common/Button';
import { useAuth } from '../../hooks/useAuth';
```

---

## 📐 Code Patterns

### Pattern #1: Page Component

```typescript
// src/pages/UserProfile.tsx
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { userService } from '@services/userService';
import { UserCard } from '@components/features/UserCard';
import { LoadingSpinner } from '@components/common/LoadingSpinner';

export const UserProfilePage: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();

  const { data: user, isLoading, error } = useQuery(
    ['user', userId],
    () => userService.getUserById(userId!),
    { enabled: !!userId }
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div>Error loading user</div>;
  if (!user) return <div>User not found</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">User Profile</h1>
      <UserCard user={user} />
    </div>
  );
};
```

### Pattern #2: Reusable Component

```typescript
// src/components/common/Button.tsx
import { ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  disabled,
  ...props
}) => {
  return (
    <button
      className={clsx(
        'btn',
        `btn-${variant}`,
        `btn-${size}`,
        isLoading && 'opacity-50 cursor-not-allowed',
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? 'Loading...' : children}
    </button>
  );
};
```

### Pattern #3: Custom Hook

```typescript
// src/hooks/useAuth.ts
import { useAuthStore } from '@stores/authStore';
import { authService } from '@services/authService';
import { useMutation } from 'react-query';
import { toast } from 'react-hot-toast';

export const useAuth = () => {
  const { user, setUser, clearUser } = useAuthStore();

  const loginMutation = useMutation(
    authService.login,
    {
      onSuccess: (data) => {
        setUser(data.user);
        localStorage.setItem('token', data.token);
        toast.success('Login successful!');
      },
      onError: (error: any) => {
        toast.error(error.message || 'Login failed');
      },
    }
  );

  const logout = () => {
    clearUser();
    localStorage.removeItem('token');
    toast.success('Logged out successfully');
  };

  return {
    user,
    isAuthenticated: !!user,
    login: loginMutation.mutate,
    logout,
    isLoggingIn: loginMutation.isLoading,
  };
};
```

### Pattern #4: API Service

```typescript
// src/service/authService.ts
import { apiClient } from '@api-request/axios';
import { LoginRequest, LoginResponse, RegisterRequest, User } from '@types/auth.types';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  async register(userData: RegisterRequest): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', userData);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },
};
```

### Pattern #5: Zustand Store

```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '@types/user.types';

interface AuthState {
  user: User | null;
  token: string | null;
  setUser: (user: User) => void;
  setToken: (token: string) => void;
  clearUser: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      clearUser: () => set({ user: null, token: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token }), // Only persist token
    }
  )
);
```

### Pattern #6: Axios Configuration

```typescript
// src/api-request/axios.ts
import axios from 'axios';
import { toast } from 'react-hot-toast';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      toast.error('Session expired. Please login again.');
    }
    return Promise.reject(error);
  }
);
```

---

## 🛣️ Routing Patterns

### Pattern #1: Main Router Setup

```typescript
// src/routes/index.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { HomePage } from '@pages/Home';
import { LoginPage } from '@pages/Login';
import { DashboardPage } from '@pages/Dashboard';

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
```

### Pattern #2: Protected Route

```typescript
// src/routes/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';

export const ProtectedRoute: React.FC = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
```

---

## 🎨 Styling Conventions

### Use Tailwind CSS Classes

```typescript
// ✅ CORRECT - Tailwind utility classes
export const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      {children}
    </div>
  );
};

// ✅ CORRECT - Conditional classes with clsx
import clsx from 'clsx';

export const Alert: React.FC<{ type: 'success' | 'error' }> = ({ type, children }) => {
  return (
    <div className={clsx(
      'p-4 rounded-md',
      type === 'success' && 'bg-green-100 text-green-800',
      type === 'error' && 'bg-red-100 text-red-800'
    )}>
      {children}
    </div>
  );
};
```

---

## 🧪 Testing Pattern

```typescript
// src/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './Button';

describe('Button', () => {
  it('renders with label', () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button label="Click me" onClick={handleClick} />);

    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button label="Click me" onClick={() => {}} disabled />);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

---

## 🤖 AI Agent Checklist

When implementing a new feature:

- [ ] **Step 1**: Define TypeScript types in `src/types/`
- [ ] **Step 2**: Create API service in `src/service/`
- [ ] **Step 3**: Create Zustand store if needed in `src/stores/`
- [ ] **Step 4**: Create custom hooks in `src/hooks/`
- [ ] **Step 5**: Create reusable components in `src/components/`
- [ ] **Step 6**: Create page component in `src/pages/`
- [ ] **Step 7**: Add route in `src/routes/index.tsx`
- [ ] **Step 8**: Write tests for components and hooks
- [ ] **Step 9**: Test in browser with `npm run dev`

---

## ✅ DO's

1. **Use TypeScript** - Type everything (props, state, API responses)
2. **Use functional components** - With hooks only
3. **Use path aliases** - `@components`, `@hooks`, etc.
4. **Use React Query** - For server state management
5. **Use Zustand** - For client state management
6. **Use React Hook Form** - For form handling
7. **Use Tailwind CSS** - For styling
8. **Handle errors** - Use try/catch and error boundaries
9. **Show loading states** - Use isLoading from React Query
10. **Use environment variables** - `import.meta.env.VITE_*`

## ❌ DON'Ts

1. **Don't use class components** - Use functional components only
2. **Don't use inline styles** - Use Tailwind classes
3. **Don't use `any` type** - Define proper types
4. **Don't fetch in components** - Use React Query hooks
5. **Don't use relative imports** - Use path aliases
6. **Don't mutate state directly** - Use setState or store actions
7. **Don't skip error handling** - Always handle errors
8. **Don't use `console.log`** - Use proper logging or remove
9. **Don't mix concerns** - Separate logic into hooks/services
10. **Don't skip TypeScript** - All files must be .ts/.tsx

---

## 🚀 Development Workflow

### Start Development Server
```bash
npm run dev
# Server runs on http://localhost:3000
```

### Build for Production
```bash
npm run build
# Output in dist/
```

### Run Tests
```bash
npm run test          # Run tests
npm run test:ui       # Run tests with UI
npm run test:coverage # Run with coverage
```

### Linting & Formatting
```bash
npm run lint          # Check for errors
npm run lint:fix      # Fix errors
npm run format        # Format code with Prettier
npm run type-check    # TypeScript type checking
```

---

## 🔧 Vite Configuration

Key configurations in `vite.config.ts`:

- **Path Aliases**: `@`, `@components`, `@pages`, `@hooks`, etc.
- **Dev Server**: Port 3000, proxy `/api` to backend
- **Build**: Code splitting for vendor, router, UI libraries
- **Test**: Vitest with jsdom environment

---

## 🌍 Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=My React App
```

Access in code:

```typescript
const apiUrl = import.meta.env.VITE_API_URL;
const appName = import.meta.env.VITE_APP_NAME;
```

---

## ⚠️ ANTI-PATTERNS

### Anti-Pattern #1: Fetching in useEffect

```typescript
// ❌ WRONG - Manual fetching in useEffect
const [user, setUser] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetch('/api/user')
    .then(res => res.json())
    .then(data => {
      setUser(data);
      setLoading(false);
    });
}, []);

// ✅ CORRECT - Use React Query
const { data: user, isLoading } = useQuery('user', () => userService.getUser());
```

### Anti-Pattern #2: Prop Drilling

```typescript
// ❌ WRONG - Passing props through many levels
<Parent user={user}>
  <Child user={user}>
    <GrandChild user={user} />
  </Child>
</Parent>

// ✅ CORRECT - Use Zustand store or Context
const { user } = useAuthStore();
```

### Anti-Pattern #3: Missing Types

```typescript
// ❌ WRONG - No types
const handleSubmit = (data) => {
  apiClient.post('/users', data);
};

// ✅ CORRECT - Typed
interface UserFormData {
  name: string;
  email: string;
}

const handleSubmit = (data: UserFormData): Promise<void> => {
  return apiClient.post('/users', data);
};
```

---

