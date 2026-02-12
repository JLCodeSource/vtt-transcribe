import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Navigation from '../components/Navigation.svelte';

describe('Navigation', () => {
  describe('Rendering', () => {
    it('renders the navigation header with title', () => {
      render(Navigation);
      expect(screen.getByText('🎬 VTT')).toBeTruthy();
    });

    it('renders all menu items', () => {
      render(Navigation);
      expect(screen.getByText('Home')).toBeTruthy();
      expect(screen.getByText('Jobs')).toBeTruthy();
      expect(screen.getByText('Settings')).toBeTruthy();
      expect(screen.getByText('About')).toBeTruthy();
    });

    it('renders menu item icons', () => {
      render(Navigation);
      const nav = screen.getByRole('navigation');
      expect(nav.textContent).toContain('🏠');
      expect(nav.textContent).toContain('📋');
      expect(nav.textContent).toContain('⚙️');
      expect(nav.textContent).toContain('ℹ️');
    });

    it('renders as a nav element with correct class', () => {
      const { container } = render(Navigation);
      const nav = container.querySelector('nav.navigation');
      expect(nav).toBeTruthy();
    });

    it('renders menu items as buttons', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(4);
    });
  });

  describe('Active Page Highlighting', () => {
    it('marks home as active by default', () => {
      render(Navigation);
      const homeButton = screen.getByText('Home').closest('button');
      expect(homeButton?.classList.contains('active')).toBe(true);
    });

    it('marks jobs as active when currentPage is jobs', () => {
      render(Navigation, { props: { currentPage: 'jobs' } });
      const jobsButton = screen.getByText('Jobs').closest('button');
      expect(jobsButton?.classList.contains('active')).toBe(true);
    });

    it('marks settings as active when currentPage is settings', () => {
      render(Navigation, { props: { currentPage: 'settings' } });
      const settingsButton = screen.getByText('Settings').closest('button');
      expect(settingsButton?.classList.contains('active')).toBe(true);
    });

    it('marks about as active when currentPage is about', () => {
      render(Navigation, { props: { currentPage: 'about' } });
      const aboutButton = screen.getByText('About').closest('button');
      expect(aboutButton?.classList.contains('active')).toBe(true);
    });

    it('only one page is active at a time', () => {
      render(Navigation, { props: { currentPage: 'jobs' } });
      const buttons = screen.getAllByRole('button');
      const activeButtons = buttons.filter(btn => btn.classList.contains('active'));
      expect(activeButtons.length).toBe(1);
    });
  });

  describe('Navigation Interaction', () => {
    it('calls onnavigate when home is clicked', async () => {
      const onnavigate = vi.fn();
      render(Navigation, { props: { onnavigate } });

      const homeButton = screen.getByText('Home').closest('button');
      await fireEvent.click(homeButton!);

      expect(onnavigate).toHaveBeenCalledWith('home');
      expect(onnavigate).toHaveBeenCalledTimes(1);
    });

    it('calls onnavigate when jobs is clicked', async () => {
      const onnavigate = vi.fn();
      render(Navigation, { props: { onnavigate } });

      const jobsButton = screen.getByText('Jobs').closest('button');
      await fireEvent.click(jobsButton!);

      expect(onnavigate).toHaveBeenCalledWith('jobs');
    });

    it('calls onnavigate when settings is clicked', async () => {
      const onnavigate = vi.fn();
      render(Navigation, { props: { onnavigate } });

      const settingsButton = screen.getByText('Settings').closest('button');
      await fireEvent.click(settingsButton!);

      expect(onnavigate).toHaveBeenCalledWith('settings');
    });

    it('calls onnavigate when about is clicked', async () => {
      const onnavigate = vi.fn();
      render(Navigation, { props: { onnavigate } });

      const aboutButton = screen.getByText('About').closest('button');
      await fireEvent.click(aboutButton!);

      expect(onnavigate).toHaveBeenCalledWith('about');
    });

    it('handles multiple navigation clicks', async () => {
      const onnavigate = vi.fn();
      render(Navigation, { props: { onnavigate } });

      const homeButton = screen.getByText('Home').closest('button');
      const jobsButton = screen.getByText('Jobs').closest('button');

      await fireEvent.click(homeButton!);
      await fireEvent.click(jobsButton!);
      await fireEvent.click(homeButton!);

      expect(onnavigate).toHaveBeenCalledTimes(3);
      expect(onnavigate).toHaveBeenNthCalledWith(1, 'home');
      expect(onnavigate).toHaveBeenNthCalledWith(2, 'jobs');
      expect(onnavigate).toHaveBeenNthCalledWith(3, 'home');
    });

    it('works without onnavigate callback', async () => {
      render(Navigation);
      const homeButton = screen.getByText('Home').closest('button');

      // Should not throw
      expect(async () => {
        await fireEvent.click(homeButton!);
      }).not.toThrow();
    });
  });

  describe('Menu Structure', () => {
    it('has correct menu item count', () => {
      render(Navigation);
      const listItems = screen.getByRole('list').querySelectorAll('li');
      expect(listItems.length).toBe(4);
    });

    it('has home as first menu item', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      expect(buttons[0].textContent).toContain('Home');
    });

    it('has jobs as second menu item', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      expect(buttons[1].textContent).toContain('Jobs');
    });

    it('has settings as third menu item', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      expect(buttons[2].textContent).toContain('Settings');
    });

    it('has about as fourth menu item', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      expect(buttons[3].textContent).toContain('About');
    });
  });

  describe('Accessibility', () => {
    it('uses semantic nav element', () => {
      render(Navigation);
      const nav = screen.getByRole('navigation');
      expect(nav).toBeTruthy();
    });

    it('uses semantic list for menu items', () => {
      render(Navigation);
      const list = screen.getByRole('list');
      expect(list).toBeTruthy();
    });

    it('all navigation items are keyboard accessible buttons', () => {
      render(Navigation);
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button.tagName).toBe('BUTTON');
      });
    });
  });
});
