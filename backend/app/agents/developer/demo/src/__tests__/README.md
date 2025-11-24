# Testing Guide

## Overview

Dự án này sử dụng Jest 30 và React Testing Library để test components và utility functions.

## Running Tests

```bash
# Chạy tất cả tests
pnpm test

# Chạy tests ở watch mode
pnpm test:watch

# Chạy tests với coverage
pnpm test:coverage
```

## Test Structure

Tests có thể được đặt ở 2 vị trí:

1. **Trong `__tests__` folder** (recommended cho nhiều test files):
   ```
   src/components/ui/__tests__/
   ├── button.test.tsx
   ├── input.test.tsx
   └── form.test.tsx
   ```

2. **Cùng cấp với file cần test**:
   ```
   src/components/
   ├── MyComponent.tsx
   └── MyComponent.test.tsx
   ```

## Writing Tests

### Component Tests

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('handles clicks', async () => {
    const handleClick = jest.fn();
    const user = userEvent.setup();
    
    render(<Button onClick={handleClick}>Click</Button>);
    await user.click(screen.getByRole('button'));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### Utility Function Tests

```typescript
import { cn } from '../utils';

describe('cn', () => {
  it('merges classes', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });
});
```

### API Route Tests

```typescript
import { GET } from '../route';

describe('API Route', () => {
  it('returns success response', async () => {
    const response = await GET();
    const data = await response.json();
    
    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
  });
});
```

## Best Practices

1. **Test behavior, not implementation**
   - Focus on what the component does, not how it does it
   - Test from the user's perspective

2. **Use descriptive test names**
   ```typescript
   // Good
   it('displays error message when form validation fails', () => {});
   
   // Bad
   it('test 1', () => {});
   ```

3. **Arrange-Act-Assert pattern**
   ```typescript
   it('increments counter', async () => {
     // Arrange
     render(<Counter />);
     const button = screen.getByRole('button');
     
     // Act
     await userEvent.click(button);
     
     // Assert
     expect(screen.getByText('Count: 1')).toBeInTheDocument();
   });
   ```

4. **Mock external dependencies**
   ```typescript
   jest.mock('@/lib/api', () => ({
     fetchData: jest.fn(() => Promise.resolve({ data: 'test' })),
   }));
   ```

5. **Clean up after tests**
   ```typescript
   afterEach(() => {
     jest.clearAllMocks();
   });
   ```

## Common Testing Queries

- `getByRole()` - Preferred, accessible
- `getByLabelText()` - For form fields
- `getByText()` - For text content
- `getByTestId()` - Last resort

## Mocked Modules

Jest setup đã mock sẵn:
- `next/navigation` (useRouter, usePathname, useSearchParams)
- `window.matchMedia`
- `IntersectionObserver`
- `ResizeObserver`

## Coverage

Xem coverage report sau khi chạy `pnpm test:coverage`:
- HTML report: `coverage/lcov-report/index.html`
- Terminal summary hiển thị ngay sau khi test

## Resources

- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

