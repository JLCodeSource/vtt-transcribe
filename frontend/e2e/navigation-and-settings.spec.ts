import { test, expect } from './fixtures';

test.describe('VTT Transcribe - Navigation', () => {
  test('should display left navigation menu', async ({ page }) => {
    // Check navigation exists
    const nav = page.locator('nav.navigation');
    await expect(nav).toBeVisible();

    // Check menu items
    await expect(page.getByRole('button', { name: 'Home' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Jobs' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Settings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'About' })).toBeVisible();
  });

  test('should navigate between pages', async ({ page }) => {
    // Navigate to About page
    await page.getByRole('button', { name: 'About' }).click();
    await expect(page.getByText('About VTT Transcribe')).toBeVisible();

    // Navigate to Jobs page
    await page.getByRole('button', { name: 'Jobs' }).click();
    await expect(page.getByText('Transcription Jobs')).toBeVisible();

    // Navigate back to Home
    await page.getByRole('button', { name: 'Home' }).click();
    await expect(page.getByText('AI-Powered Video Transcription')).toBeVisible();
  });

  test('should open settings from navigation', async ({ page }) => {
    // Click settings in nav
    await page.getByRole('button', { name: 'Settings' }).click();

    // Settings modal should open
    const settingsModal = page.getByRole('dialog', { name: 'Settings' });
    await expect(settingsModal).toBeVisible();
    await expect(page.getByRole('heading', { name: '⚙️ Settings' })).toBeVisible();
  });
});

test.describe('VTT Transcribe - User Menu', () => {
  test('should display user menu in top right', async ({ page }) => {
    // Check user menu exists
    const userMenu = page.locator('.user-menu');
    await expect(userMenu).toBeVisible();
    await expect(page.getByText('testuser')).toBeVisible();
  });

  test('should open user menu dropdown', async ({ page }) => {
    // Click user menu button
    await page.getByRole('button', { name: 'User menu' }).click();

    // Dropdown should appear - check Logout button in the dropdown menu
    await expect(page.getByRole('banner').getByRole('button', { name: 'Logout' })).toBeVisible();
  });

  test('should open settings from user menu', async ({ page }) => {
    // Open user menu
    await page.getByRole('button', { name: 'User menu' }).click();

    // Click settings in dropdown (from banner/header, not navigation)
    await page.getByRole('banner').getByRole('button', { name: 'Settings' }).click();

    // Settings modal should open
    await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible();
  });
});

test.describe('VTT Transcribe - Settings Modal', () => {
  test('should display translation section', async ({ page }) => {
    // Open settings (from navigation list, not dropdown)
    await page.getByRole('list').getByRole('button', { name: 'Settings' }).click();

    // Check Translation section exists
    await expect(page.getByRole('heading', { name: 'Translation' })).toBeVisible();

    // Check translation dropdown
    await expect(page.getByLabel('Target Language')).toBeVisible();

    // API Configuration section should NOT exist
    await expect(page.getByText('API Configuration')).not.toBeVisible();
    await expect(page.getByLabel('OpenAI API Key')).not.toBeVisible();
  });

  test('should have language dropdown with options', async ({ page }) => {
    await page.getByRole('list').getByRole('button', { name: 'Settings' }).click();

    const langSelect = page.getByLabel('Target Language');

    // Check default value
    await expect(langSelect).toHaveValue('none');

    // Check some language options exist (options in select are not individually visible, check they exist)
    await expect(langSelect.locator('option[value="es"]')).toHaveCount(1);
    await expect(langSelect.locator('option[value="fr"]')).toHaveCount(1);
    await expect(langSelect.locator('option[value="de"]')).toHaveCount(1);

    // Select a language
    await langSelect.selectOption('es');
    await expect(langSelect).toHaveValue('es');
  });

  test('should close settings modal', async ({ page }) => {
    await page.getByRole('button', { name: 'Settings' }).first().click();

    // Modal should be visible
    await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible();

    // Click cancel button
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Modal should close
    await expect(page.getByRole('dialog', { name: 'Settings' })).not.toBeVisible();
  });

  test('should save translation settings to sessionStorage', async ({ page }) => {
    await page.getByRole('button', { name: 'Settings' }).first().click();

    // Fill in translation language
    await page.getByLabel('Target Language').selectOption('es');

    // Save
    await page.getByRole('button', { name: 'Save Settings' }).click();

    // Check sessionStorage for translation language only
    const lang = await page.evaluate(() => sessionStorage.getItem('translation_language'));
    expect(lang).toBe('es');

    // API key should NOT be in sessionStorage
    const openaiKey = await page.evaluate(() => sessionStorage.getItem('openai_api_key'));
    expect(openaiKey).toBeNull();
  });
});
