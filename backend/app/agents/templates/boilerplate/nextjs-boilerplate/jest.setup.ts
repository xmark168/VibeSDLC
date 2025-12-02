// Polyfills must be defined BEFORE any imports that use them
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Fetch API - use native Node.js fetch (available in Node 18+)
// If not available, tests that need fetch should mock it
if (typeof global.fetch === 'undefined') {
  global.fetch = jest.fn();
  global.Response = jest.fn() as any;
  global.Request = jest.fn() as any;
  global.Headers = jest.fn() as any;
}

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    };
  },
  usePathname() {
    return '/';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;

// Mock next/server for API route testing
jest.mock('next/server', () => {
  return {
    NextResponse: {
      json: (data: any, init?: ResponseInit) => {
        const response = new Response(JSON.stringify(data), {
          ...init,
          headers: {
            'content-type': 'application/json',
            ...init?.headers,
          },
        });
        return response;
      },
      redirect: (url: string | URL) => {
        return new Response(null, {
          status: 307,
          headers: { Location: url.toString() },
        });
      },
      next: () => new Response(null),
    },
    NextRequest: class NextRequest extends Request {
      nextUrl: URL;
      constructor(input: RequestInfo | URL, init?: RequestInit) {
        super(input, init);
        this.nextUrl = new URL(
          typeof input === 'string'
            ? input
            : input instanceof URL
              ? input.href
              : input.url
        );
      }
    },
  };
});

