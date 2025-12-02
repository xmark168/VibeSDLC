---
name: state-management
description: Manage client-side state with Zustand. Use when building shopping cart, user preferences, theme toggle, UI state, or any cross-component shared state with localStorage persist.
---

# State Management (Zustand 5)

## Critical Rules

1. **File location**: `lib/stores/<name>-store.ts`
2. **Use `create`** - NOT createStore
3. **Persist** với localStorage khi cần
4. **Keep stores small** - 1 store per domain
5. **Use selectors** - Tránh re-render không cần thiết
6. **'use client'** - Required in components using store

## Quick Reference

### Basic Store
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

### With Persist (localStorage)
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
    { name: 'theme-storage' }
  )
);
```

### Using in Component
```tsx
'use client';
import { useCartStore } from '@/lib/stores/cart-store';

export function CartButton() {
  // Selector - chỉ re-render khi items.length thay đổi
  const count = useCartStore((state) => state.items.length);
  return <button>Cart ({count})</button>;
}

export function CartTotal() {
  const total = useCartStore((state) => state.total());
  return <span>${total.toFixed(2)}</span>;
}
```

### Multiple Selectors
```tsx
'use client';
import { useShallow } from 'zustand/react/shallow';
import { useCartStore } from '@/lib/stores/cart-store';

export function CartSummary() {
  // useShallow prevents re-render if object values unchanged
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

## References

- `zustand-patterns.md` - Advanced patterns, devtools, testing
