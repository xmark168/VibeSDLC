---
name: unit-test
description: Write unit tests with Jest and React Testing Library. Use when testing components, utilities, server actions, or API routes. CRITICAL - Uses Jest (NOT Vitest).
---

This skill guides creation of comprehensive unit tests that cover all important scenarios.

The user needs to test components, utility functions, or server-side logic.

## Before You Start

**CRITICAL**: This project uses Jest, NOT Vitest.

NEVER use: `import { vi } from 'vitest'`, `vi.fn()`, `vi.mock()`

ALWAYS use: `jest.fn()`, `jest.mock()`, `jest.spyOn()`, `jest.clearAllMocks()` in beforeEach

## Required Test Categories

For each function, include these test types:

**1. Happy Path** - Core logic with valid input
- Normal, expected input
- Correct result per business requirements

**2. Edge Cases** - Boundary and extreme values
- Empty input ([], "", null, undefined)
- Single item vs many items
- Very small / very large values

**3. Invalid Input** - Error handling
- Wrong type, null, undefined
- Invalid format, non-existent data
- Must throw correct error or return error state

**4. Business Rules** - Domain logic branches
- Each if/else condition
- VIP vs regular, thresholds, discounts

**5. Boundary Testing** - Values at threshold
- If condition `>= N`: test N-1, N, N+1
- Catches off-by-one bugs

**6. Side Effects** - Dependencies (DB, API)
- Mock returns success -> verify behavior
- Mock returns error -> verify error handling

## Heuristics for Test Generation

**For each public function:**
- Min 1 happy path test
- Min 1 test per important if/else branch
- Min 1 test for empty/null input

**Code pattern rules:**
- `if x > N` -> test x = N-1, N, N+1
- Loop on list -> test [], [1], [many items]
- Try/catch -> test exception path

**Dependency calls:**
- Test success response
- Test error response

## Priority Functions

Focus testing on:
- **Hot paths**: Frequently called functions
- **Money/stats**: Calculations, points, balances
- **Security**: Auth, permissions, validation

## Test Count Guideline

- Simple utility: 3-5 tests
- Function with conditions: 6-8 tests
- Complex business logic: 8-12 tests

## Test File Structure

```typescript
describe('FeatureName', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('happy path', () => {
    it('returns correct result with valid input', () => { });
  });

  describe('edge cases', () => {
    it('handles empty array', () => { });
    it('handles null input', () => { });
    it('handles single item', () => { });
  });

  describe('boundary values', () => {
    it('handles value at threshold', () => { });
    it('handles value below threshold', () => { });
    it('handles value above threshold', () => { });
  });

  describe('business rules', () => {
    it('applies VIP discount', () => { });
    it('applies regular pricing', () => { });
  });

  describe('error handling', () => {
    it('throws on invalid input', () => { });
    it('handles API error', () => { });
  });
});
```

## Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('Component', () => {
  it('renders with valid props', () => {
    render(<Component items={[item1, item2]} />);
    expect(screen.getByText(/item1/i)).toBeInTheDocument();
  });

  it('handles empty props', () => {
    render(<Component items={[]} />);
    expect(screen.getByText(/no items/i)).toBeInTheDocument();
  });

  it('handles undefined props', () => {
    render(<Component items={undefined as any} />);
    // Should not crash
  });
});
```

## Mocking

```typescript
jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: jest.fn(),
      create: jest.fn(),
    },
  },
}));

// Success case
(prisma.user.findUnique as jest.Mock).mockResolvedValue({ id: '1' });

// Error case
(prisma.user.findUnique as jest.Mock).mockRejectedValue(new Error('DB error'));
```

## Pre-configured Mocks

Already in `jest.setup.ts`:
- `next/navigation` (useRouter, usePathname)
- `next/server` (NextResponse, NextRequest)
- Browser APIs (matchMedia, IntersectionObserver)

## Commands

```bash
bun test              # Run all
bun test --watch      # Watch mode
bun test --coverage   # Coverage report
```

NEVER:
- Import from vitest
- Skip beforeEach with jest.clearAllMocks()
- Write only happy path tests
- Ignore boundary conditions

**IMPORTANT**: Every function with conditions needs boundary tests. If there's a threshold, test N-1, N, N+1.
