# Page Object Model for Playwright

## Why Page Objects?

- **Reusability**: Define selectors once, use everywhere
- **Maintainability**: Update selectors in one place
- **Readability**: Tests read like user stories
- **Encapsulation**: Hide implementation details

## Basic Structure

### Login Page
```typescript
// e2e/pages/login.page.ts
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Login' });
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectError(message: string) {
    await expect(this.errorMessage).toContainText(message);
  }
}
```

### Dashboard Page
```typescript
// e2e/pages/dashboard.page.ts
import { Page, Locator, expect } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly welcomeMessage: Locator;
  readonly logoutButton: Locator;
  readonly userMenu: Locator;

  constructor(page: Page) {
    this.page = page;
    this.welcomeMessage = page.getByRole('heading', { name: /welcome/i });
    this.logoutButton = page.getByRole('button', { name: 'Logout' });
    this.userMenu = page.getByTestId('user-menu');
  }

  async expectToBeVisible() {
    await expect(this.page).toHaveURL('/dashboard');
    await expect(this.welcomeMessage).toBeVisible();
  }

  async logout() {
    await this.userMenu.click();
    await this.logoutButton.click();
  }
}
```

### Signup Page
```typescript
// e2e/pages/signup.page.ts
import { Page, Locator } from '@playwright/test';

export class SignupPage {
  readonly page: Page;
  readonly nameInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.nameInput = page.getByLabel('Name');
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.confirmPasswordInput = page.getByLabel('Confirm Password');
    this.submitButton = page.getByRole('button', { name: 'Sign Up' });
  }

  async goto() {
    await this.page.goto('/signup');
  }

  async signup(name: string, email: string, password: string) {
    await this.nameInput.fill(name);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(password);
    await this.submitButton.click();
  }
}
```

## Using Page Objects in Tests

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/login.page';
import { DashboardPage } from './pages/dashboard.page';
import { SignupPage } from './pages/signup.page';

test.describe('Authentication', () => {
  test('user can login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);

    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    await dashboardPage.expectToBeVisible();
  });

  test('shows error for invalid login', async ({ page }) => {
    const loginPage = new LoginPage(page);

    await loginPage.goto();
    await loginPage.login('wrong@example.com', 'wrongpassword');
    await loginPage.expectError('Invalid credentials');
  });

  test('user can signup', async ({ page }) => {
    const signupPage = new SignupPage(page);
    const dashboardPage = new DashboardPage(page);

    await signupPage.goto();
    await signupPage.signup('New User', 'newuser@example.com', 'SecurePass123!');
    await dashboardPage.expectToBeVisible();
  });

  test('user can logout', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);

    // Login
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    await dashboardPage.expectToBeVisible();

    // Logout
    await dashboardPage.logout();
    await expect(page).toHaveURL('/');
  });
});
```

## Component Page Objects

For reusable components:

```typescript
// e2e/components/navbar.component.ts
import { Page, Locator } from '@playwright/test';

export class NavbarComponent {
  readonly page: Page;
  readonly logo: Locator;
  readonly homeLink: Locator;
  readonly profileLink: Locator;
  readonly settingsLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.logo = page.getByRole('link', { name: 'Logo' });
    this.homeLink = page.getByRole('link', { name: 'Home' });
    this.profileLink = page.getByRole('link', { name: 'Profile' });
    this.settingsLink = page.getByRole('link', { name: 'Settings' });
  }

  async navigateToHome() {
    await this.homeLink.click();
  }

  async navigateToProfile() {
    await this.profileLink.click();
  }
}
```

## Fixtures for Page Objects

```typescript
// e2e/fixtures.ts
import { test as base } from '@playwright/test';
import { LoginPage } from './pages/login.page';
import { DashboardPage } from './pages/dashboard.page';

type Pages = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
};

export const test = base.extend<Pages>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
});

export { expect } from '@playwright/test';
```

### Using Fixtures
```typescript
// e2e/auth.spec.ts
import { test, expect } from './fixtures';

test('user can login', async ({ loginPage, dashboardPage }) => {
  await loginPage.goto();
  await loginPage.login('test@example.com', 'password123');
  await dashboardPage.expectToBeVisible();
});
```

## Best Practices

1. **One file per page** - Keep page objects focused
2. **Meaningful method names** - `login()` not `fillFormAndSubmit()`
3. **No assertions in page objects** - Keep assertions in tests (except for `expectToBeVisible`)
4. **Use getByRole first** - Better accessibility
5. **Lazy initialization** - Create page objects when needed
