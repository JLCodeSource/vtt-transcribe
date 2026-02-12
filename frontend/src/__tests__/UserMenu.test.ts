import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import UserMenu from '../components/UserMenu.svelte';

describe('UserMenu', () => {
  describe('Rendering - Logged Out State', () => {
    it('renders with guest username by default', () => {
      render(UserMenu);
      expect(screen.getByText('Guest')).toBeTruthy();
    });

    it('shows generic avatar icon when logged out', () => {
      render(UserMenu);
      const avatar = screen.getByText('👤');
      expect(avatar).toBeTruthy();
    });

    it('renders the user menu button', () => {
      render(UserMenu);
      const button = screen.getByLabelText('User menu');
      expect(button).toBeTruthy();
    });

    it('shows chevron down indicator', () => {
      const { container } = render(UserMenu);
      const chevron = container.querySelector('.chevron');
      expect(chevron?.textContent).toBe('▼');
    });

    it('dropdown menu is hidden initially', () => {
      const { container } = render(UserMenu);
      const dropdown = container.querySelector('.dropdown-menu');
      expect(dropdown).toBeFalsy();
    });
  });

  describe('Rendering - Logged In State', () => {
    it('shows username when provided', () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'John' } });
      expect(screen.getByText('John')).toBeTruthy();
    });

    it('shows first letter of username in avatar when logged in', () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      expect(screen.getByText('A')).toBeTruthy();
    });

    it('uppercases first letter in avatar', () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'bob' } });
      expect(screen.getByText('B')).toBeTruthy();
    });

    it('handles single character username', () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'X' } });
      // Both avatar and username show 'X', use getAllByText
      const xElements = screen.getAllByText('X');
      expect(xElements.length).toBe(2); // Avatar and username
    });

    it('handles long username', () => {
      const longName = 'VeryLongUsername';
      render(UserMenu, { props: { isLoggedIn: true, username: longName } });
      expect(screen.getByText(longName)).toBeTruthy();
      expect(screen.getByText('V')).toBeTruthy(); // First letter only in avatar
    });
  });

  describe('Menu Toggle Interaction', () => {
    it('opens dropdown when button is clicked', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');

      await fireEvent.click(button);

      const dropdown = container.querySelector('.dropdown-menu');
      expect(dropdown).toBeTruthy();
    });

    it('closes dropdown when button is clicked again', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');

      await fireEvent.click(button);
      await fireEvent.click(button);

      const dropdown = container.querySelector('.dropdown-menu');
      expect(dropdown).toBeFalsy();
    });

    it('rotates chevron when menu opens', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');
      const chevron = container.querySelector('.chevron');

      expect(chevron?.classList.contains('open')).toBe(false);

      await fireEvent.click(button);

      expect(chevron?.classList.contains('open')).toBe(true);
    });

    it('rotates chevron back when menu closes', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');
      const chevron = container.querySelector('.chevron');

      await fireEvent.click(button);
      await fireEvent.click(button);

      expect(chevron?.classList.contains('open')).toBe(false);
    });
  });

  describe('Dropdown Menu Content - Logged Out', () => {
    beforeEach(async () => {
      render(UserMenu);
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);
    });

    it('shows API key configuration message when logged out', () => {
      expect(screen.getByText('Configure your API keys in Settings')).toBeTruthy();
    });

    it('shows Settings menu item', () => {
      expect(screen.getByText('Settings')).toBeTruthy();
    });

    it('shows settings icon', () => {
      expect(screen.getByText('⚙️')).toBeTruthy();
    });

    it('does not show Logout option when logged out', () => {
      expect(screen.queryByText('Logout')).toBeFalsy();
    });

    it('does not show menu divider when logged out', () => {
      const { container } = render(UserMenu);
      const divider = container.querySelector('.menu-divider');
      expect(divider).toBeFalsy();
    });
  });

  describe('Dropdown Menu Content - Logged In', () => {
    it('shows Settings menu item when logged in', async () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      expect(screen.getByText('Settings')).toBeTruthy();
    });

    it('shows Logout menu item when logged in', async () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      expect(screen.getByText('Logout')).toBeTruthy();
    });

    it('shows logout icon when logged in', async () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      expect(screen.getByText('🚪')).toBeTruthy();
    });

    it('does not show API key message when logged in', async () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      expect(screen.queryByText('Configure your API keys in Settings')).toBeFalsy();
    });

    it('shows menu divider before logout', async () => {
      const { container } = render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const divider = container.querySelector('.menu-divider');
      expect(divider).toBeTruthy();
    });
  });

  describe('Settings Click Handler', () => {
    it('calls onsettings callback when Settings is clicked', async () => {
      const onsettings = vi.fn();
      render(UserMenu, { props: { onsettings } });

      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const settingsButton = screen.getByText('Settings').closest('button');
      await fireEvent.click(settingsButton!);

      expect(onsettings).toHaveBeenCalledTimes(1);
    });

    it('closes menu after Settings is clicked', async () => {
      const onsettings = vi.fn();
      const { container } = render(UserMenu, { props: { onsettings } });

      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const settingsButton = screen.getByText('Settings').closest('button');
      await fireEvent.click(settingsButton!);

      const dropdown = container.querySelector('.dropdown-menu');
      expect(dropdown).toBeFalsy();
    });

    it('works without onsettings callback', async () => {
      render(UserMenu);
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const settingsButton = screen.getByText('Settings').closest('button');

      // Should not throw or reject
      await fireEvent.click(settingsButton!);
    });
  });

  describe('Logout Click Handler', () => {
    it('calls onlogout callback when Logout is clicked', async () => {
      const onlogout = vi.fn();
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice', onlogout } });

      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const logoutButton = screen.getByText('Logout').closest('button');
      await fireEvent.click(logoutButton!);

      expect(onlogout).toHaveBeenCalledTimes(1);
    });

    it('closes menu after Logout is clicked', async () => {
      const onlogout = vi.fn();
      const { container } = render(UserMenu, { props: { isLoggedIn: true, username: 'Alice', onlogout } });

      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const logoutButton = screen.getByText('Logout').closest('button');
      await fireEvent.click(logoutButton!);

      const dropdown = container.querySelector('.dropdown-menu');
      expect(dropdown).toBeFalsy();
    });

    it('works without onlogout callback', async () => {
      render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const logoutButton = screen.getByText('Logout').closest('button');

      // Should not throw or reject
      await fireEvent.click(logoutButton!);
    });
  });

  describe('Click Outside Behavior', () => {
    it('closes menu when clicking outside', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');

      await fireEvent.click(button);
      expect(container.querySelector('.dropdown-menu')).toBeTruthy();

      // Simulate click outside
      await fireEvent.click(document.body);

      expect(container.querySelector('.dropdown-menu')).toBeFalsy();
    });

    it('keeps menu open when clicking inside menu', async () => {
      const { container } = render(UserMenu);
      const button = screen.getByLabelText('User menu');

      await fireEvent.click(button);

      const dropdown = container.querySelector('.dropdown-menu');
      await fireEvent.click(dropdown!);

      expect(container.querySelector('.dropdown-menu')).toBeTruthy();
    });

    it('does nothing when clicking outside while menu is closed', async () => {
      const { container } = render(UserMenu);

      await fireEvent.click(document.body);

      expect(container.querySelector('.dropdown-menu')).toBeFalsy();
    });
  });

  describe('Accessibility', () => {
    it('user menu button has aria-label', () => {
      render(UserMenu);
      const button = screen.getByLabelText('User menu');
      expect(button.getAttribute('aria-label')).toBe('User menu');
    });

    it('all menu items are keyboard accessible buttons', async () => {
      const { container } = render(UserMenu, { props: { isLoggedIn: true } });
      const button = screen.getByLabelText('User menu');
      await fireEvent.click(button);

      const menuButtons = container.querySelectorAll('.menu-item');
      menuButtons.forEach(btn => {
        expect(btn.tagName).toBe('BUTTON');
      });
    });
  });

  describe('Multiple User Scenarios', () => {
    it('handles transition from logged out to logged in', async () => {
      const { rerender } = render(UserMenu, { props: { isLoggedIn: false, username: 'Guest' } });
      expect(screen.getByText('👤')).toBeTruthy();

      rerender({ isLoggedIn: true, username: 'Alice' });
      expect(screen.getByText('A')).toBeTruthy();
      expect(screen.getByText('Alice')).toBeTruthy();
    });

    it('handles username change while logged in', async () => {
      const { rerender } = render(UserMenu, { props: { isLoggedIn: true, username: 'Alice' } });
      expect(screen.getByText('Alice')).toBeTruthy();

      rerender({ isLoggedIn: true, username: 'Bob' });
      expect(screen.getByText('Bob')).toBeTruthy();
      expect(screen.getByText('B')).toBeTruthy();
    });
  });
});
