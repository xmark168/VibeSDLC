# React + Vite Application

A modern React application template built with Vite, TypeScript, and Tailwind CSS.

## 🚀 Features

- **React 18** - Latest React with concurrent features
- **Vite** - Lightning fast build tool and dev server
- **TypeScript** - Type safety and better developer experience
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Zustand** - Lightweight state management
- **React Hook Form** - Performant forms with easy validation
- **Vitest** - Fast unit testing framework
- **ESLint + Prettier** - Code linting and formatting
- **Hot Toast** - Beautiful toast notifications

## 📋 Requirements

- Node.js 18+
- npm 8+ or yarn 1.22+

## 🛠️ Installation

1. **Install dependencies**:
```bash
npm install
# or
yarn install
```

2. **Environment setup**:
```bash
cp .env.example .env.local
# Edit .env.local with your configuration
```

3. **Start development server**:
```bash
npm run dev
# or
yarn dev
```

The application will be available at `http://localhost:3000`

## 🧪 Testing

```bash
# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## 🏗️ Building

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Basic UI components
│   ├── forms/          # Form components
│   └── layout/         # Layout components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── services/           # API services
├── stores/             # Zustand stores
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── styles/             # Global styles
└── test/               # Test utilities
```

## 🎨 Styling

This template uses Tailwind CSS for styling. Key features:

- **Responsive design** - Mobile-first approach
- **Dark mode support** - Built-in dark mode toggle
- **Custom components** - Pre-built UI components
- **Consistent spacing** - Standardized spacing scale

## 🔐 Authentication

The template includes a complete authentication system:

- **Login/Register** - User authentication
- **Protected routes** - Route-level protection
- **Token management** - Automatic token handling
- **Persistent sessions** - Login state persistence

## 📡 API Integration

- **Axios** - HTTP client with interceptors
- **React Query** - Server state management
- **Error handling** - Centralized error handling
- **Loading states** - Built-in loading indicators

## 🛠️ Development

### Code Quality

```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format

# Type checking
npm run type-check
```

### Environment Variables

Create a `.env.local` file:

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=React Vite App
VITE_ENABLE_DEVTOOLS=true
```

### Custom Hooks

The template includes several custom hooks:

- `useAuth` - Authentication state and actions
- `useApi` - API calls with loading states
- `useLocalStorage` - Local storage management
- `useDebounce` - Debounced values

## 🚀 Deployment

### Vercel

```bash
npm install -g vercel
vercel
```

### Netlify

```bash
npm run build
# Upload dist/ folder to Netlify
```

### Docker

```bash
# Build image
docker build -t react-vite-app .

# Run container
docker run -p 3000:3000 react-vite-app
```

## 🔧 Configuration

### Vite Configuration

Key configurations in `vite.config.ts`:

- **Path aliases** - Import shortcuts
- **Proxy setup** - API proxy for development
- **Build optimization** - Code splitting and optimization

### Tailwind Configuration

Customize in `tailwind.config.js`:

- **Colors** - Brand colors and theme
- **Fonts** - Typography settings
- **Breakpoints** - Responsive breakpoints

## 📚 Scripts

- `dev` - Start development server
- `build` - Build for production
- `preview` - Preview production build
- `test` - Run tests
- `lint` - Lint code
- `format` - Format code
- `type-check` - TypeScript type checking

## 📝 License

This project is licensed under the MIT License.
