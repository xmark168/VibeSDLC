import { test, expect } from '@playwright/test';

test.describe('User Login', () => {
  test('user can login with valid credentials', async ({ page }) => {
    // Arrange: Go to login page
    await page.goto('/signin');

    // Act: Fill in valid credentials and submit
    await page.getByLabel('Email').fill('test@example.com');
    await page.getByLabel('Password').fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Assert: Redirected to dashboard (or home) and see welcome message
    await expect(page).toHaveURL(/dashboard|\/$/);
    await expect(
      page.getByText(/welcome|dashboard/i, { exact: false })
    ).toBeVisible();
  });

  test('shows error for invalid credentials', async ({ page }) => {
    // Arrange: Go to login page
    await page.goto('/signin');

    // Act: Fill in invalid credentials and submit
    await page.getByLabel('Email').fill('wrong@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Assert: Error message is visible and still on login page
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
    await expect(page).toHaveURL('/signin');
  });
});
