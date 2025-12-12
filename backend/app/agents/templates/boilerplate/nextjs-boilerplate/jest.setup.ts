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

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
    span: 'span',
    h1: 'h1',
    h2: 'h2',
    h3: 'h3',
    p: 'p',
    a: 'a',
    button: 'button',
    section: 'section',
    article: 'article',
    nav: 'nav',
    ul: 'ul',
    li: 'li',
    img: 'img',
    form: 'form',
    input: 'input',
    header: 'header',
    footer: 'footer',
    main: 'main',
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  useAnimation: () => ({ start: jest.fn(), stop: jest.fn() }),
  useInView: () => [null, true],
  useScroll: () => ({ scrollY: { get: () => 0 } }),
  useTransform: () => 0,
  useMotionValue: () => ({ get: () => 0, set: jest.fn() }),
  useSpring: () => ({ get: () => 0, set: jest.fn() }),
}));

// Mock next/server for API route testing
jest.mock('next/server', () => {
  // Mock cookies implementation
  class MockRequestCookies {
    private cookies: Map<string, string> = new Map();
    
    get(name: string) {
      const value = this.cookies.get(name);
      return value ? { name, value } : undefined;
    }
    
    getAll() {
      return Array.from(this.cookies.entries()).map(([name, value]) => ({ name, value }));
    }
    
    has(name: string) {
      return this.cookies.has(name);
    }
    
    set(name: string, value: string) {
      this.cookies.set(name, value);
    }
    
    delete(name: string) {
      this.cookies.delete(name);
    }
  }

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
        // Ensure json() method exists for jest environment
        (response as any).json = async () => data;
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
      cookies: MockRequestCookies;
      private _url: string;
      
      constructor(input: RequestInfo | URL, init?: RequestInit) {
        // Ensure URL string is properly passed to Request
        const url = typeof input === 'string'
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
        super(url, init);
        this._url = url;
        this.nextUrl = new URL(url);
        this.cookies = new MockRequestCookies();
      }
      
      // Override url getter to ensure it returns the correct value
      get url() {
        return this._url;
      }
      
      get geo() {
        return { city: undefined, country: undefined, region: undefined };
      }
      
      get ip() {
        return '127.0.0.1';
      }
    },
  };
});

