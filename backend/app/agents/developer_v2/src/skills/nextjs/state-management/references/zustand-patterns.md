# Zustand Advanced Patterns

## Selector Patterns

### Single Value Selector
```typescript
// Good - only re-renders when count changes
const count = useStore((state) => state.items.length);

// Bad - re-renders on any state change
const { items } = useStore();
```

### Multiple Values with useShallow
```typescript
import { useShallow } from 'zustand/react/shallow';

// Good - shallow comparison prevents unnecessary re-renders
const { name, email } = useUserStore(
  useShallow((state) => ({ name: state.name, email: state.email }))
);
```

### Computed/Derived Values
```typescript
import { useMemo } from 'react';

function CartTotal() {
  const items = useCartStore((state) => state.items);
  
  const total = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items]
  );
  
  return <span>{total}</span>;
}
```

## Reset Store Pattern

```typescript
interface UserStore {
  user: User | null;
  isLoggedIn: boolean;
  login: (user: User) => void;
  logout: () => void;
  reset: () => void;
}

const initialState = {
  user: null,
  isLoggedIn: false,
};

export const useUserStore = create<UserStore>((set) => ({
  ...initialState,
  login: (user) => set({ user, isLoggedIn: true }),
  logout: () => set(initialState),
  reset: () => set(initialState),
}));
```

## Devtools Middleware

```typescript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useStore = create<MyStore>()(
  devtools(
    (set) => ({
      // state and actions
    }),
    { name: 'MyStore' } // Shows in Redux DevTools
  )
);
```

## Combined Middlewares

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export const useCartStore = create<CartStore>()(
  devtools(
    persist(
      (set) => ({
        items: [],
        addItem: (item) => set((state) => ({ items: [...state.items, item] })),
      }),
      { name: 'cart-storage' }
    ),
    { name: 'CartStore' }
  )
);
```

## Async Actions

```typescript
interface ProductStore {
  products: Product[];
  loading: boolean;
  error: string | null;
  fetchProducts: () => Promise<void>;
}

export const useProductStore = create<ProductStore>((set) => ({
  products: [],
  loading: false,
  error: null,
  fetchProducts: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch('/api/products');
      const products = await res.json();
      set({ products, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch', loading: false });
    }
  },
}));
```

## SSR Hydration (Next.js)

```typescript
// lib/stores/cart-store.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export const useCartStore = create<CartStore>()(
  persist(
    (set) => ({
      items: [],
      // actions...
    }),
    {
      name: 'cart-storage',
      storage: createJSONStorage(() => localStorage),
      skipHydration: true, // Important for SSR
    }
  )
);
```

```tsx
// components/cart-provider.tsx
'use client';
import { useEffect } from 'react';
import { useCartStore } from '@/lib/stores/cart-store';

export function CartProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    useCartStore.persist.rehydrate();
  }, []);

  return <>{children}</>;
}
```

## Testing Stores

```typescript
// __tests__/stores/cart-store.test.ts
import { useCartStore } from '@/lib/stores/cart-store';

describe('CartStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useCartStore.setState({ items: [] });
  });

  it('adds item to cart', () => {
    const item = { id: '1', name: 'Product', price: 10, quantity: 1 };
    
    useCartStore.getState().addItem(item);
    
    expect(useCartStore.getState().items).toHaveLength(1);
    expect(useCartStore.getState().items[0]).toEqual(item);
  });

  it('removes item from cart', () => {
    useCartStore.setState({
      items: [{ id: '1', name: 'Product', price: 10, quantity: 1 }],
    });
    
    useCartStore.getState().removeItem('1');
    
    expect(useCartStore.getState().items).toHaveLength(0);
  });

  it('calculates total correctly', () => {
    useCartStore.setState({
      items: [
        { id: '1', name: 'A', price: 10, quantity: 2 },
        { id: '2', name: 'B', price: 5, quantity: 3 },
      ],
    });
    
    expect(useCartStore.getState().total()).toBe(35);
  });
});
```

## Store Slices Pattern (Large Apps)

```typescript
// lib/stores/slices/cart-slice.ts
export interface CartSlice {
  items: CartItem[];
  addItem: (item: CartItem) => void;
}

export const createCartSlice = (set: SetState): CartSlice => ({
  items: [],
  addItem: (item) => set((state) => ({ items: [...state.items, item] })),
});

// lib/stores/slices/user-slice.ts
export interface UserSlice {
  user: User | null;
  setUser: (user: User) => void;
}

export const createUserSlice = (set: SetState): UserSlice => ({
  user: null,
  setUser: (user) => set({ user }),
});

// lib/stores/app-store.ts
import { create } from 'zustand';
import { createCartSlice, CartSlice } from './slices/cart-slice';
import { createUserSlice, UserSlice } from './slices/user-slice';

type AppStore = CartSlice & UserSlice;

export const useAppStore = create<AppStore>()((...args) => ({
  ...createCartSlice(...args),
  ...createUserSlice(...args),
}));
```

## Common Patterns Summary

| Pattern | Use Case |
|---------|----------|
| Basic `create` | Simple UI state |
| `persist` | User preferences, cart |
| `devtools` | Development debugging |
| Selectors | Performance optimization |
| `useShallow` | Multiple values selection |
| Reset pattern | Auth logout, form reset |
| Slices | Large applications |
