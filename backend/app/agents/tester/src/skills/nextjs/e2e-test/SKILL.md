---
name: e2e-test
description: Write E2E tests with Playwright for full user flows. Use when testing complete user journeys, UI interactions, or cross-page navigation.
---

# E2E Test (Playwright)

## ⚠️ CRITICAL RULES - READ FIRST
- **DO NOT** create config files (jest.config.*, playwright.config.*, tsconfig.json)
- Config files **ALREADY EXIST** in project - use them as-is
- **ONLY** create TEST files: *.spec.ts in e2e/ folder
- **READ SOURCE CODE FIRST** - Check actual page routes, components, selectors before writing tests
- **DO NOT INVENT SELECTORS** - Only use selectors that exist in the actual HTML

## ⚠️ INVALID MATCHERS - DO NOT USE THESE
```typescript
// ❌ THESE DO NOT EXIST IN PLAYWRIGHT - WILL CAUSE TYPESCRIPT ERRORS
await expect(locator).toHaveCountGreaterThan(5);     // DOES NOT EXIST
await expect(locator).toHaveCountLessThan(10);       // DOES NOT EXIST
await expect(locator).toHaveCountGreaterThanOrEqual(5);  // DOES NOT EXIST
await expect(page).toHaveURL({ gt: 0 });             // INVALID SYNTAX

// ✅ USE THESE INSTEAD
await expect(locator).toHaveCount(5);                // Exact count
const count = await locator.count();
expect(count).toBeGreaterThan(5);                    // Use Jest matcher on count
expect(count).toBeLessThan(10);
```

## ✅ VALID PLAYWRIGHT MATCHERS
```typescript
// Page assertions
await expect(page).toHaveURL('/dashboard');
await expect(page).toHaveURL(/.*dashboard/);
await expect(page).toHaveTitle('Dashboard');

// Locator assertions
await expect(locator).toBeVisible();
await expect(locator).toBeHidden();
await expect(locator).toBeEnabled();
await expect(locator).toBeDisabled();
await expect(locator).toBeChecked();
await expect(locator).toHaveText('Hello');
await expect(locator).toContainText('Hello');
await expect(locator).toHaveValue('input value');
await expect(locator).toHaveAttribute('href', '/home');
await expect(locator).toHaveClass(/active/);
await expect(locator).toHaveCount(5);               // EXACT count only
await expect(locator).toHaveCSS('color', 'red');
```

## When to Use
- Testing complete user flows (signup → login → dashboard)
- Testing UI interactions and navigation
- Testing forms with validation
- Testing responsive behavior
- Testing authentication flows

## File Location
Place tests in e2e/ folder: `e2e/story-{slug}.spec.ts`

## Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature: User Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('user can sign up successfully', async ({ page }) => {
    // Navigate to signup
    await page.click('text=Sign Up');
    await expect(page).toHaveURL('/signup');
    
    // Fill form
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="email"]', 'newuser@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.fill('[name="confirmPassword"]', 'SecurePass123!');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Assert success
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Welcome')).toBeVisible();
  });

  test('user can login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/dashboard');
  });

  test('shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[name="email"]', 'wrong@example.com');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
    await expect(page).toHaveURL('/login');
  });

  test('user can logout', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
    
    // Logout
    await page.click('button:has-text("Logout")');
    await expect(page).toHaveURL('/');
  });
});
```

## Locator Strategies (Priority Order)

1. **getByRole** - Best for accessibility
```typescript
await page.getByRole('button', { name: 'Submit' }).click();
await page.getByRole('link', { name: 'Sign Up' }).click();
await page.getByRole('textbox', { name: 'Email' }).fill('test@example.com');
```

2. **getByLabel** - For form inputs
```typescript
await page.getByLabel('Email').fill('test@example.com');
await page.getByLabel('Password').fill('password123');
```

3. **getByText** - For visible text
```typescript
await page.getByText('Welcome back').click();
```

4. **getByTestId** - Last resort
```typescript
await page.getByTestId('submit-button').click();
```

## Common Assertions

```typescript
// Visibility
await expect(page.locator('.error')).toBeVisible();
await expect(page.locator('.loading')).toBeHidden();

// URL
await expect(page).toHaveURL('/dashboard');
await expect(page).toHaveURL(/.*dashboard/);

// Text content
await expect(page.locator('h1')).toHaveText('Dashboard');
await expect(page.locator('.message')).toContainText('Success');

// Attributes
await expect(page.locator('input')).toHaveValue('test@example.com');
await expect(page.locator('button')).toBeDisabled();
await expect(page.locator('input')).toHaveAttribute('type', 'email');

// Count
await expect(page.locator('.item')).toHaveCount(5);
```

## Waiting Strategies

```typescript
// Wait for element
await page.waitForSelector('.loaded');

// Wait for URL
await page.waitForURL('/dashboard');

// Wait for network idle
await page.waitForLoadState('networkidle');

// Wait for response
await page.waitForResponse(resp => resp.url().includes('/api/users'));

// Custom wait
await expect(page.locator('.spinner')).toBeHidden({ timeout: 10000 });
```

## Commands
```bash
npx playwright test                    # Run all E2E
npx playwright test auth.spec.ts       # Run specific file
npx playwright test --ui               # Interactive UI mode
npx playwright test --headed           # See browser
npx playwright test --debug            # Debug mode
npx playwright show-report             # View HTML report
npx playwright codegen                 # Generate tests by recording
```

## Tips

1. **Use baseURL** - Don't hardcode full URLs
2. **Explicit waits** - Use `expect().toBeVisible()` instead of arbitrary timeouts
3. **Isolation** - Each test should be independent
4. **Test IDs** - Add `data-testid` for complex selectors
5. **Screenshots** - Use `await page.screenshot()` for debugging

## References
- `page-objects.md` - Page Object Model examples
