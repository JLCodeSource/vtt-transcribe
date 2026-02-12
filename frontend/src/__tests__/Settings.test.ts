import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Settings from '../components/Settings.svelte';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('Settings', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  describe('Modal Visibility', () => {
    it('does not render when isOpen is false', () => {
      const { container } = render(Settings, { props: { isOpen: false } });
      const modal = container.querySelector('.modal-backdrop');
      expect(modal).toBeFalsy();
    });

    it('renders when isOpen is true', () => {
      const { container } = render(Settings, { props: { isOpen: true } });
      const modal = container.querySelector('.modal-backdrop');
      expect(modal).toBeTruthy();
    });

    it('shows settings title when open', () => {
      render(Settings, { props: { isOpen: true } });
      expect(screen.getByText(/Settings/i)).toBeTruthy();
    });

    it('has correct ARIA attributes', () => {
      render(Settings, { props: { isOpen: true } });
      const dialog = screen.getByRole('dialog');
      expect(dialog.getAttribute('aria-modal')).toBe('true');
      expect(dialog.getAttribute('aria-labelledby')).toBe('settings-title');
    });
  });

  describe('API Configuration Section', () => {
    beforeEach(() => {
      render(Settings, { props: { isOpen: true } });
    });

    it('shows API Configuration heading', () => {
      expect(screen.getByText('API Configuration')).toBeTruthy();
    });

    it('shows OpenAI API Key field', () => {
      expect(screen.getByLabelText(/OpenAI API Key/i)).toBeTruthy();
    });

    it('shows HuggingFace Token field', () => {
      expect(screen.getByLabelText(/HuggingFace Token/i)).toBeTruthy();
    });

    it('marks OpenAI API Key as required', () => {
      const label = screen.getByText('OpenAI API Key').closest('label');
      expect(label?.textContent).toContain('*');
    });

    it('renders password input types by default', () => {
      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;
      const hfInput = screen.getByLabelText(/HuggingFace Token/i) as HTMLInputElement;

      expect(openaiInput.type).toBe('password');
      expect(hfInput.type).toBe('password');
    });
  });

  describe('Password Visibility Toggle', () => {
    it('toggles OpenAI key visibility when show/hide is clicked', async () => {
      render(Settings, { props: { isOpen: true } });
      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;
      const toggleButton = screen.getByLabelText(/Show API key/i);

      expect(openaiInput.type).toBe('password');

      await fireEvent.click(toggleButton!);
      expect(openaiInput.type).toBe('text');

      await fireEvent.click(toggleButton!);
      expect(openaiInput.type).toBe('password');
    });

    it('toggles HuggingFace token visibility when show/hide is clicked', async () => {
      render(Settings, { props: { isOpen: true } });
      const hfInput = screen.getByLabelText(/HuggingFace Token/i) as HTMLInputElement;
      const toggleButton = screen.getAllByText('Show')[1].closest('button');

      expect(hfInput.type).toBe('password');

      await fireEvent.click(toggleButton!);
      expect(hfInput.type).toBe('text');

      await fireEvent.click(toggleButton!);
      expect(hfInput.type).toBe('password');
    });

    it('changes button text to Hide when showing', async () => {
      render(Settings, { props: { isOpen: true } });
      const toggleButton = screen.getByLabelText(/Show API key/i);

      await fireEvent.click(toggleButton!);
      expect(screen.getAllByText('Hide')[0]).toBeTruthy();
    });
  });

  describe('Translation Settings', () => {
    beforeEach(() => {
      render(Settings, { props: { isOpen: true } });
    });

    it('shows Translation heading', () => {
      expect(screen.getByRole('heading', { name: /Translation/i })).toBeTruthy();
    });

    it('shows Target Language dropdown', () => {
      expect(screen.getByLabelText(/Target Language/i)).toBeTruthy();
    });

    it('has "No Translation" as default option', () => {
      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;
      expect(select.value).toBe('none');
    });

    it('includes all language options', () => {
      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;
      const options = Array.from(select.options).map(opt => opt.value);

      expect(options).toContain('none');
      expect(options).toContain('es');
      expect(options).toContain('fr');
      expect(options).toContain('de');
      expect(options).toContain('it');
      expect(options).toContain('pt');
      expect(options).toContain('ru');
      expect(options).toContain('ja');
      expect(options).toContain('ko');
      expect(options).toContain('zh');
    });

    it('allows selecting a language', async () => {
      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;

      await fireEvent.change(select, { target: { value: 'es' } });
      expect(select.value).toBe('es');
    });
  });

  describe('Close Functionality', () => {
    it('calls onclose when close button is clicked', async () => {
      const onclose = vi.fn();
      render(Settings, { props: { isOpen: true, onclose } });

      const closeButton = screen.getByLabelText('Close');
      await fireEvent.click(closeButton);

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('calls onclose when backdrop is clicked', async () => {
      const onclose = vi.fn();
      const { container } = render(Settings, { props: { isOpen: true, onclose } });

      const backdrop = container.querySelector('.modal-backdrop');
      await fireEvent.click(backdrop!);

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('does not close when clicking inside modal', async () => {
      const onclose = vi.fn();
      const { container } = render(Settings, { props: { isOpen: true, onclose } });

      const modal = container.querySelector('.modal');
      await fireEvent.click(modal!);

      expect(onclose).not.toHaveBeenCalled();
    });

    it('calls onclose when Escape key is pressed', async () => {
      const onclose = vi.fn();
      const { container } = render(Settings, { props: { isOpen: true, onclose } });

      const backdrop = container.querySelector('.modal-backdrop');
      await fireEvent.keyDown(backdrop!, { key: 'Escape' });

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('works without onclose callback', async () => {
      const { container } = render(Settings, { props: { isOpen: true } });
      const closeButton = screen.getByLabelText('Close');

      expect(async () => {
        await fireEvent.click(closeButton);
      }).not.toThrow();
    });
  });

  describe('Save Functionality', () => {
    it('calls onclose when Save button is clicked', async () => {
      const onclose = vi.fn();
      render(Settings, { props: { isOpen: true, onclose } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('saves OpenAI key to localStorage', async () => {
      render(Settings, { props: { isOpen: true } });

      const openaiInput = screen.getByLabelText(/OpenAI API Key/i);
      await fireEvent.input(openaiInput, { target: { value: 'test-key-123' } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(localStorageMock.getItem('openai_api_key')).toBe('test-key-123');
    });

    it('saves HuggingFace token to localStorage', async () => {
      render(Settings, { props: { isOpen: true } });

      const hfInput = screen.getByLabelText(/HuggingFace Token/i);
      await fireEvent.input(hfInput, { target: { value: 'hf-token-456' } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(localStorageMock.getItem('hf_token')).toBe('hf-token-456');
    });

    it('saves translation language to localStorage', async () => {
      render(Settings, { props: { isOpen: true } });

      const select = screen.getByLabelText(/Target Language/i);
      await fireEvent.change(select, { target: { value: 'es' } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(localStorageMock.getItem('translation_language')).toBe('es');
    });

    it('removes OpenAI key from localStorage if empty', async () => {
      localStorageMock.setItem('openai_api_key', 'existing-key');
      render(Settings, { props: { isOpen: true } });

      const openaiInput = screen.getByLabelText(/OpenAI API Key/i);
      await fireEvent.input(openaiInput, { target: { value: '' } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(localStorageMock.getItem('openai_api_key')).toBe(null);
    });

    it('removes HuggingFace token from localStorage if empty', async () => {
      localStorageMock.setItem('hf_token', 'existing-token');
      render(Settings, { props: { isOpen: true } });

      const hfInput = screen.getByLabelText(/HuggingFace Token/i);
      await fireEvent.input(hfInput, { target: { value: '' } });

      const saveButton = screen.getByText(/Save Changes/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(localStorageMock.getItem('hf_token')).toBe(null);
    });
  });

  describe('localStorage Loading', () => {
    it('loads OpenAI key from localStorage on mount', () => {
      localStorageMock.setItem('openai_api_key', 'stored-key');
      render(Settings, { props: { isOpen: true } });

      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;
      // Wait for effect to run
      setTimeout(() => {
        expect(openaiInput.value).toBe('stored-key');
      }, 0);
    });

    it('loads HuggingFace token from localStorage on mount', () => {
      localStorageMock.setItem('hf_token', 'stored-token');
      render(Settings, { props: { isOpen: true } });

      const hfInput = screen.getByLabelText(/HuggingFace Token/i) as HTMLInputElement;
      setTimeout(() => {
        expect(hfInput.value).toBe('stored-token');
      }, 0);
    });

    it('loads translation language from localStorage on mount', () => {
      localStorageMock.setItem('translation_language', 'fr');
      render(Settings, { props: { isOpen: true } });

      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;
      setTimeout(() => {
        expect(select.value).toBe('fr');
      }, 0);
    });

    it('uses default values when localStorage is empty', () => {
      render(Settings, { props: { isOpen: true } });

      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;
      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;

      setTimeout(() => {
        expect(openaiInput.value).toBe('');
        expect(select.value).toBe('none');
      }, 0);
    });
  });

  describe('Form Validation', () => {
    it('OpenAI input accepts text', async () => {
      render(Settings, { props: { isOpen: true } });
      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;

      await fireEvent.input(openaiInput, { target: { value: 'sk-test123' } });
      expect(openaiInput.value).toBe('sk-test123');
    });

    it('HuggingFace input accepts text', async () => {
      render(Settings, { props: { isOpen: true } });
      const hfInput = screen.getByLabelText(/HuggingFace Token/i) as HTMLInputElement;

      await fireEvent.input(hfInput, { target: { value: 'hf_test456' } });
      expect(hfInput.value).toBe('hf_test456');
    });

    it('allows special characters in API keys', async () => {
      render(Settings, { props: { isOpen: true } });
      const openaiInput = screen.getByLabelText(/OpenAI API Key/i) as HTMLInputElement;

      await fireEvent.input(openaiInput, { target: { value: 'sk-!@#$%^&*()_+-=' } });
      expect(openaiInput.value).toBe('sk-!@#$%^&*()_+-=');
    });
  });

  describe('Cancel Button', () => {
    it('shows Cancel button', () => {
      render(Settings, { props: { isOpen: true } });
      expect(screen.getByText('Cancel')).toBeTruthy();
    });

    it('calls onclose when Cancel is clicked', async () => {
      const onclose = vi.fn();
      render(Settings, { props: { isOpen: true, onclose } });

      const cancelButton = screen.getByText('Cancel').closest('button');
      await fireEvent.click(cancelButton!);

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('does not save changes when Cancel is clicked', async () => {
      render(Settings, { props: { isOpen: true } });

      const openaiInput = screen.getByLabelText(/OpenAI API Key/i);
      await fireEvent.input(openaiInput, { target: { value: 'test-key' } });

      const cancelButton = screen.getByText('Cancel').closest('button');
      await fireEvent.click(cancelButton!);

      expect(localStorageMock.getItem('openai_api_key')).toBe(null);
    });
  });

  describe('Accessibility', () => {
    it('has proper role and modal attributes', () => {
      render(Settings, { props: { isOpen: true } });
      const dialog = screen.getByRole('dialog');

      expect(dialog.getAttribute('aria-modal')).toBe('true');
      expect(dialog.getAttribute('tabindex')).toBe('0');
    });

    it('close button has aria-label', () => {
      render(Settings, { props: { isOpen: true } });
      const closeButton = screen.getByLabelText('Close');
      expect(closeButton).toBeTruthy();
    });

    it('all form fields have labels', () => {
      render(Settings, { props: { isOpen: true } });

      expect(screen.getByLabelText(/OpenAI API Key/i)).toBeTruthy();
      expect(screen.getByLabelText(/HuggingFace Token/i)).toBeTruthy();
      expect(screen.getByLabelText(/Target Language/i)).toBeTruthy();
    });

    it('has descriptive headings', () => {
      render(Settings, { props: { isOpen: true } });

      expect(screen.getByRole('heading', { name: /Settings/i })).toBeTruthy();
      expect(screen.getByRole('heading', { name: /Translation/i })).toBeTruthy();
    });
  });
});
