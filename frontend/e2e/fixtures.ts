import { test as base, expect } from '@playwright/test';

/**
 * Extended test fixture that provides authenticated session
 * Registers a test user and logs in before each test
 */
export const test = base.extend({
  // Automatically login before each test
  page: async ({ page }, use) => {
    // Navigate to app
    await page.goto('/');

    // Check if login form is visible
    const loginHeading = page.getByRole('heading', { name: /Sign In/i });
    const isLoginVisible = await loginHeading.isVisible().catch(() => false);

    if (isLoginVisible) {
      // Try to register test user (will fail if already exists, which is fine)
      try {
        const registerResponse = await page.request.post('/auth/register', {
          data: {
            username: 'testuser',
            email: 'test@example.com',
            password: 'testpass123',
          },
        });
        // Ignore 400 errors (user already exists)
        if (registerResponse.status() !== 201 && registerResponse.status() !== 400) {
          console.warn(`Registration returned status ${registerResponse.status()}`);
        }
      } catch (error) {
        // Registration might fail if user exists, continue to login
        console.log('Registration skipped, continuing to login');
      }

      // Login with test credentials
      const usernameInput = page.getByLabel(/username/i);
      const passwordInput = page.getByLabel(/password/i);
      const submitButton = page.getByRole('button', { name: /sign in/i });

      await usernameInput.fill('testuser');
      await passwordInput.fill('testpass123');
      await submitButton.click();

      // Wait for successful login (file upload should appear)
      await expect(page.getByText(/Drop your video file here/i)).toBeVisible({ timeout: 15000 });
    }

    // Use the authenticated page
    await use(page);
  },
});

export { expect };
