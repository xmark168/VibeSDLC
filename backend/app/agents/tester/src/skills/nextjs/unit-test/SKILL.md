---
name: unit-test
description: Unit tests with Jest + React Testing Library. CRITICAL - Uses Jest (NOT Vitest).
---

# Unit Test (Jest + Testing Library)

## ⚠️ JEST ONLY - NOT Vitest
```typescript
//  Jest globals (no import needed)
jest.fn(), jest.mock(), jest.clearAllMocks()

// Vitest (will fail!)
import { vi } from 'vitest'  // ERROR!
```

---

## ⭐⭐⭐ MINIMALIST: 1-2 TESTS PER COMPONENT ⭐⭐⭐

### Rule: ONE comprehensive test > MANY brittle tests

| Component Type | Max Tests | Focus |
|----------------|-----------|-------|
| Static (no fetch) | 1 | Renders with props |
| Async (with fetch) | 2 | Heading + loaded data |

### DO NOT TEST (will cause failures):
- Empty state
- Error state
- Loading skeletons
- Each element separately
- Elements that may not exist

###  Combine multiple assertions in ONE test:
```typescript
it('renders correctly', async () => {
  // Multiple expects in ONE test = good
  expect(heading).toBeInTheDocument();
  expect(item1).toBeInTheDocument();
  expect(item2).toBeInTheDocument();
});
```

---

## ⭐ TEMPLATE (1-2 tests per component)

```typescript
import { render, screen, waitFor, act } from '@testing-library/react';
import { MySection } from '@/components/home/MySection';

// Suppress Next.js Image warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (args[0]?.includes?.('React does not recognize')) return;
    if (args[0]?.includes?.('received `true` for a non-boolean')) return;
    originalError(...args);
  };
});
afterAll(() => {
  console.error = originalError;
});

describe('MySection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        data: [
          { id: '1', title: 'Item 1', author: 'Author 1' },
          { id: '2', title: 'Item 2', author: 'Author 2' },
        ],
      }),
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  //  TEST 1: Renders section correctly (REQUIRED)
  it('renders section with heading and content', async () => {
    await act(async () => {
      render(<MySection />);
    });

    // Static content (heading)
    expect(screen.getByRole('heading', { name: /my section/i })).toBeInTheDocument();

    // Dynamic content (after fetch)
    await waitFor(() => {
      expect(screen.getByText(/item 1/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/item 2/i)).toBeInTheDocument();
  });

  //  TEST 2: Links/interactions (OPTIONAL - only if component has links)
  it('renders navigation link', async () => {
    await act(async () => {
      render(<MySection />);
    });

    const link = screen.getByRole('link', { name: /view all/i });
    expect(link.getAttribute('href')).toContain('/items');
  });
});
// DONE! 2 tests = complete coverage for this component
```

---

## ⛔ CRITICAL RULES

### 1. ASYNC: Use `act()` + `waitFor()`
```typescript
await act(async () => { render(<Component />); });
await waitFor(() => { expect(screen.getByText(/data/i)).toBeInTheDocument(); });
```

### 2. MULTIPLE ELEMENTS: Use `getAllByText()` or `getByRole()`
```typescript
//  Text appears multiple times
const elements = screen.getAllByText(/science/i);
expect(elements.length).toBeGreaterThan(0);

//  Be specific with role
expect(screen.getByRole('heading', { name: /science/i })).toBeInTheDocument();
```

### 3. CASE-INSENSITIVE: Always use `/i` flag
```typescript
screen.getByText(/featured books/i);  // 
screen.getByText('Featured Books');   // ❌
```

### 4. LINKS: Flexible href matching
```typescript
expect(link.getAttribute('href')).toContain('/books');  // 
expect(link).toHaveAttribute('href', '/books');         // ❌
```

### 5. ONLY TEST WHAT EXISTS IN SOURCE CODE
```typescript
//  Read source code first
expect(screen.getByRole('heading')).toBeInTheDocument();

// Don't assume elements exist
expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument(); // May not exist!
```

---

## 🔧 MOCK FETCH

```typescript
beforeEach(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ success: true, data: [...] }),
  });
});
```

---

## 📋 QUERY PRIORITY

| Priority | Query | Use Case |
|----------|-------|----------|
| 1 | `getByRole` | Buttons, links, headings |
| 2 | `getByText` | Static text (use `/i`) |
| 3 | `getAllByText` | Text appears multiple times |

---

## ANTI-PATTERNS

| Don't | Why |
|-------|-----|
| 5+ tests per component | Too many failure points |
| Test empty/error states | Component may not have them |
| Test loading skeletons | Data loads sync in Jest |
| Separate test per element | Combine in one test |
| `import { vi } from 'vitest'` | Use Jest, not Vitest |
