---
name: state-management
description: Manage client-side state with Zustand. Use when building shopping cart, user preferences, theme toggle, UI state, or any cross-component shared state with localStorage persist.
---

This skill guides implementation of client-side state management using Zustand.

The user needs to share state between components, persist data to localStorage, or manage complex UI state like shopping carts or theme preferences.

## Before You Start

Zustand is the preferred state management library:
- **File location**: `lib/stores/<name>-store.ts`
- **Function**: Use `create` from zustand (NOT createStore)
- **Components**: Must have `'use client'` to use stores

**CRITICAL**: Keep stores small and focused. Create one store per domain (cart, theme, user preferences) rather than one large store.

## Basic Store

```typescript
// lib/stores/cart-store.ts
import { create } from 'zustand';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  total: () => number;
}

export const useCartStore = create<CartStore>((set, get) => ({
  items: [],
  
  addItem: (item) =>
    set((state) => {
      const existing = state.items.find((i) => i.id === item.id);
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.id === item.id ? { ...i, quantity: i.quantity + item.quantity } : i
          ),
        };
      }
      return { items: [...state.items, item] };
    }),
    
  removeItem: (id) =>
    set((state) => ({
      items: state.items.filter((i) => i.id !== id),
    })),
    
  updateQuantity: (id, quantity) =>
    set((state) => ({
      items: state.items.map((i) => (i.id === id ? { ...i, quantity } : i)),
    })),
    
  clearCart: () => set({ items: [] }),
  
  total: () => get().items.reduce((sum, i) => sum + i.price * i.quantity, 0),
}));
```

## Store with localStorage Persistence

Use the `persist` middleware for data that should survive page refresh:

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeStore {
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'light',
      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
    }),
    { name: 'theme-storage' }  // localStorage key
  )
);
```

## Using Stores in Components

Always use selectors to prevent unnecessary re-renders:

```tsx
'use client';
import { useCartStore } from '@/lib/stores/cart-store';

export function CartButton() {
  // Selector - only re-renders when items.length changes
  const count = useCartStore((state) => state.items.length);
  return <button>Cart ({count})</button>;
}

export function CartTotal() {
  const total = useCartStore((state) => state.total());
  return <span>${total.toFixed(2)}</span>;
}
```

## Multiple Selectors with useShallow

When selecting multiple values, use `useShallow` to prevent re-renders if values haven't changed:

```tsx
'use client';
import { useShallow } from 'zustand/react/shallow';
import { useCartStore } from '@/lib/stores/cart-store';

export function CartSummary() {
  const { items, total } = useCartStore(
    useShallow((state) => ({
      items: state.items,
      total: state.total(),
    }))
  );

  return (
    <div>
      <p>{items.length} items</p>
      <p>Total: ${total.toFixed(2)}</p>
    </div>
  );
}
```

## Accessing Actions

Actions don't cause re-renders, so you can select them directly:

```tsx
'use client';
import { useCartStore } from '@/lib/stores/cart-store';

export function AddToCartButton({ product }) {
  const addItem = useCartStore((state) => state.addItem);
  
  return (
    <button onClick={() => addItem({ ...product, quantity: 1 })}>
      Add to Cart
    </button>
  );
}
```

NEVER:
- Use `createStore` (use `create` instead)
- Select the entire store without selectors (causes unnecessary re-renders)
- Forget `'use client'` in components using stores
- Create one giant store (split by domain)
- Access stores in Server Components

**IMPORTANT**: Zustand stores are client-side only. For server-side state, use Server Components with direct database queries.
