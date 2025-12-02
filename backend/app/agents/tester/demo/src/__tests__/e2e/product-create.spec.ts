import { test, expect } from '@playwright/test';

// E2E: Product Creation Flow

test.describe('Product Creation', () => {
  test.beforeEach(async ({ page }) => {
    // Arrange: Go to the product creation page (assume /products/new)
    await page.goto('/products/new');
  });

  test('admin can create product via UI', async ({ page }) => {
    // Arrange: Fill out the product creation form
    await page.getByLabel('Name').fill('Test Product');
    await page.getByLabel('Description').fill('A test product for E2E');
    await page.getByLabel('Price').fill('19.99');
    // Act: Submit the form
    await page.getByRole('button', { name: /create/i }).click();
    // Assert: Success message and redirect to product list or detail
    await expect(page.getByText('Product created successfully')).toBeVisible();
    // Optionally, check redirect
    // await expect(page).toHaveURL(/\/products\//);
  });

  test('shows error for missing required fields', async ({ page }) => {
    // Arrange: Leave required fields empty and submit
    await page.getByRole('button', { name: /create/i }).click();
    // Assert: Error messages are shown
    await expect(page.getByText('Name is required')).toBeVisible();
    await expect(page.getByText('Price is required')).toBeVisible();
  });
});
