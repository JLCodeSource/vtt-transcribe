import { test as base, expect } from '@playwright/test';

/**
 * Extended test fixture that provides authenticated session
 * Registers a test user and logs in before each test
 */
export const test = base.extend({
  // Automatically login before each test
  page: async ({ page }, use) => {
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ username: 'testuser', email: 'test@example.com' }),
      });
    });

    await page.route('**/oauth/providers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ providers: [] }),
      });
    });

    await page.addInitScript(() => {
      window.localStorage.setItem('access_token', 'e2e-test-token');
      window.localStorage.setItem('username', 'testuser');
    });

    await page.goto('/');
    await expect(page.getByText(/Drop your video file here/i)).toBeVisible({ timeout: 15000 });

    // Use the authenticated page
    await use(page);
  },
});

export { expect };
