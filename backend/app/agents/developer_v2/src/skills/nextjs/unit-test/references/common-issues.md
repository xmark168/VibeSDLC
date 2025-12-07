# Common Testing Issues & Solutions

## Text Split Across Elements

**Error:** `TestingLibraryElementError: Unable to find an element with the text: X. This could be because the text is broken up by multiple elements.`

**Cause:** Text rendered inside nested elements like:
```html
<div data-slot="card">
  <span>James</span> <span>Stewart</span>
</div>
```

**Solutions:**

```typescript
// Will fail if text is split
screen.getByText('James Stewart');

// Solution 1: Custom function matcher (recommended)
screen.getByText((content, element) => {
  return element?.textContent === 'James Stewart';
});

// Solution 2: Regex (case-insensitive, partial match)
screen.getByText(/james stewart/i);

// Solution 3: Use within() to narrow scope
import { within } from '@testing-library/react';
const card = screen.getByRole('article'); // or getByTestId
within(card).getByText(/james/i);

// Solution 4: Query by test id (last resort)
screen.getByTestId('author-name');
```

---

## Element Not Found After Async Update

**Error:** `Unable to find an element...` after state update

**Solutions:**

```typescript
// Immediate query fails
render(<Component />);
expect(screen.getByText('Loaded')).toBeInTheDocument();

// Use findBy (auto-waits)
const element = await screen.findByText('Loaded');

// Or wrap in waitFor
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});
```

---

## Multiple Elements Found

**Error:** `Found multiple elements with the text: X`

**Solutions:**

```typescript
// Multiple matches
screen.getByText('Submit');

// Use getAllBy and index
const buttons = screen.getAllByText('Submit');
expect(buttons[0]).toBeInTheDocument();

// Use more specific query
screen.getByRole('button', { name: /submit form/i });

// Use within() to scope
const form = screen.getByRole('form');
within(form).getByText('Submit');
```

---

## Act Warning

**Warning:** `Warning: An update to Component inside a test was not wrapped in act(...)`

**Solutions:**

```typescript
// Wrap state updates
import { act } from '@testing-library/react';

await act(async () => {
  fireEvent.click(button);
});

// Or use userEvent (auto-wraps in act)
const user = userEvent.setup();
await user.click(button);

// Use waitFor for async updates
await waitFor(() => {
  expect(screen.getByText('Updated')).toBeInTheDocument();
});
```
