import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import Settings from '../components/Settings.svelte';

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

describe('Settings', () => {
  beforeEach(() => {
    sessionStorageMock.clear();
  });

  afterEach(() => {
    sessionStorageMock.clear();
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
      expect(screen.getByRole('heading', { name: /Settings/i })).toBeTruthy();
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

    it('does NOT show API Configuration section', () => {
      expect(screen.queryByText('API Configuration')).toBeFalsy();
    });

    it('does NOT show OpenAI API Key field', () => {
      expect(screen.queryByLabelText(/OpenAI API Key/i)).toBeFalsy();
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
      render(Settings, { props: { isOpen: true } });
      const closeButton = screen.getByLabelText('Close');

      // Should not throw or reject
      await fireEvent.click(closeButton);
    });
  });

  describe('Save Functionality', () => {
    it('calls onclose when Save button is clicked', async () => {
      const onclose = vi.fn();
      render(Settings, { props: { isOpen: true, onclose } });

      const saveButton = screen.getByText(/Save Settings/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(onclose).toHaveBeenCalledTimes(1);
    });

    it('saves translation language to sessionStorage', async () => {
      render(Settings, { props: { isOpen: true } });

      const select = screen.getByLabelText(/Target Language/i);
      await fireEvent.change(select, { target: { value: 'es' } });

      const saveButton = screen.getByText(/Save Settings/i).closest('button');
      await fireEvent.click(saveButton!);

      expect(sessionStorageMock.getItem('translation_language')).toBe('es');
    });
  });

  describe('sessionStorage Loading', () => {
    it('loads translation language from sessionStorage on mount', async () => {
      sessionStorageMock.setItem('translation_language', 'fr');
      render(Settings, { props: { isOpen: true } });

      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;
      await waitFor(() => {
        expect(select.value).toBe('fr');
      });
    });

    it('uses default values when sessionStorage is empty', async () => {
      render(Settings, { props: { isOpen: true } });

      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;

      await waitFor(() => {
        expect(select.value).toBe('none');
      });
    });
  });

  describe('Form Validation', () => {
    it('translation select works correctly', async () => {
      render(Settings, { props: { isOpen: true } });
      const select = screen.getByLabelText(/Target Language/i) as HTMLSelectElement;

      await fireEvent.change(select, { target: { value: 'es' } });
      expect(select.value).toBe('es');
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

      const select = screen.getByLabelText(/Target Language/i);
      await fireEvent.change(select, { target: { value: 'fr' } });

      const cancelButton = screen.getByText('Cancel').closest('button');
      await fireEvent.click(cancelButton!);

      expect(sessionStorageMock.getItem('translation_language')).toBe(null);
    });
  });

  describe('Accessibility', () => {
    it('has proper role and modal attributes', () => {
      render(Settings, { props: { isOpen: true } });
      const dialog = screen.getByRole('dialog');

      expect(dialog.getAttribute('aria-modal')).toBe('true');
      expect(dialog.getAttribute('tabindex')).toBe('-1');
    });

    it('close button has aria-label', () => {
      render(Settings, { props: { isOpen: true } });
      const closeButton = screen.getByLabelText('Close');
      expect(closeButton).toBeTruthy();
    });

    it('all form fields have labels', () => {
      render(Settings, { props: { isOpen: true } });

      expect(screen.getByLabelText(/Target Language/i)).toBeTruthy();
    });

    it('has descriptive headings', () => {
      render(Settings, { props: { isOpen: true } });

      expect(screen.getByRole('heading', { name: /Settings/i })).toBeTruthy();
      expect(screen.getByRole('heading', { name: /Translation/i })).toBeTruthy();
    });
  });
});
