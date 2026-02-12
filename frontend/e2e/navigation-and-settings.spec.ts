import { test, expect } from '@playwright/test';

test.describe('VTT Transcribe - Navigation', () => {
  test('should display left navigation menu', async ({ page }) => {
    await page.goto('/');
    
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
    await page.goto('/');
    
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
    await page.goto('/');
    
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
    await page.goto('/');
    
    // Check user menu exists
    const userMenu = page.locator('.user-menu');
    await expect(userMenu).toBeVisible();
    await expect(page.getByText('Guest')).toBeVisible();
  });

  test('should open user menu dropdown', async ({ page }) => {
    await page.goto('/');
    
    // Click user menu button
    await page.getByRole('button', { name: 'User menu' }).click();
    
    // Dropdown should appear
    await expect(page.getByText('Configure your API keys in Settings')).toBeVisible();
    // Check Settings button in the dropdown menu (in header/banner, not navigation)
    await expect(page.getByRole('banner').getByRole('button', { name: 'Settings' })).toBeVisible();
  });

  test('should open settings from user menu', async ({ page }) => {
    await page.goto('/');
    
    // Open user menu
    await page.getByRole('button', { name: 'User menu' }).click();
    
    // Click settings in dropdown (from banner/header, not navigation)
    await page.getByRole('banner').getByRole('button', { name: 'Settings' }).click();
    
    // Settings modal should open
    await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible();
  });
});

test.describe('VTT Transcribe - Settings Modal', () => {
  test('should display all settings sections', async ({ page }) => {
    await page.goto('/');
    
    // Open settings (from navigation list, not dropdown)
    await page.getByRole('list').getByRole('button', { name: 'Settings' }).click();
    
    // Check sections exist
    await expect(page.getByText('API Configuration')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Translation' })).toBeVisible();
    
    // Check OpenAI API key field
    await expect(page.getByLabel('OpenAI API Key')).toBeVisible();
    
    // Check HuggingFace token field
    await expect(page.getByLabel('HuggingFace Token')).toBeVisible();
    
    // Check translation dropdown
    await expect(page.getByLabel('Target Language')).toBeVisible();
  });

  test('should allow entering API keys', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    
    // Enter OpenAI key
    const openaiInput = page.getByLabel('OpenAI API Key');
    await openaiInput.fill('sk-test-1234567890');
    await expect(openaiInput).toHaveValue('sk-test-1234567890');
    
    // Enter HF token
    const hfInput = page.getByLabel('HuggingFace Token');
    await hfInput.fill('hf_test_token');
    await expect(hfInput).toHaveValue('hf_test_token');
  });

  test('should toggle password visibility', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    
    const openaiInput = page.getByLabel('OpenAI API Key');
    await openaiInput.fill('sk-secret-key');
    
    // Input should be password type initially
    await expect(openaiInput).toHaveAttribute('type', 'password');
    
    // Click toggle button
    await page.getByRole('button', { name: 'Show API key' }).click();
    
    // Input should now be text type
    await expect(openaiInput).toHaveAttribute('type', 'text');
  });

  test('should have language dropdown with options', async ({ page }) => {
    await page.goto('/');
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
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    
    // Modal should be visible
    await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible();
    
    // Click cancel button
    await page.getByRole('button', { name: 'Cancel' }).click();
    
    // Modal should close
    await expect(page.getByRole('dialog', { name: 'Settings' })).not.toBeVisible();
  });

  test('should save settings to sessionStorage', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).first().click();
    
    // Fill in settings
    await page.getByLabel('OpenAI API Key').fill('sk-test-key');
    await page.getByLabel('HuggingFace Token').fill('hf_test');
    await page.getByLabel('Target Language').selectOption('es');
    
    // Save
    await page.getByRole('button', { name: 'Save Settings' }).click();
    
    // Check sessionStorage
    const openaiKey = await page.evaluate(() => sessionStorage.getItem('openai_api_key'));
    const hfToken = await page.evaluate(() => sessionStorage.getItem('hf_token'));
    const lang = await page.evaluate(() => sessionStorage.getItem('translation_language'));
    
    expect(openaiKey).toBe('sk-test-key');
    expect(hfToken).toBe('hf_test');
    expect(lang).toBe('es');
  });
});
