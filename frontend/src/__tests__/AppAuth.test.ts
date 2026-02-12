import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import App from '../App.svelte';

// Mock fetch globally
global.fetch = vi.fn();

describe('App with Auth Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('shows login form when not authenticated', () => {
    render(App);
    expect(screen.getByRole('heading', { name: /Sign In/i })).toBeTruthy();
  });

  it('hides file upload when not authenticated', () => {
    render(App);
    expect(screen.queryByText(/Drop your video file here/i)).toBeFalsy();
  });

  it('shows file upload after successful login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'fake-token', token_type: 'bearer' }),
    });

    render(App);

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await fireEvent.input(usernameInput, { target: { value: 'testuser' } });
    await fireEvent.input(passwordInput, { target: { value: 'password123' } });
    await fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Drop your video file here/i)).toBeTruthy();
    });
  });

  it('shows error message on failed login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Incorrect username or password' }),
    });

    render(App);

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await fireEvent.input(usernameInput, { target: { value: 'testuser' } });
    await fireEvent.input(passwordInput, { target: { value: 'wrongpassword' } });
    await fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Incorrect username or password/i)).toBeTruthy();
    });
  });

  it('updates UserMenu with username after login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'fake-token', token_type: 'bearer' }),
    });

    render(App);

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await fireEvent.input(usernameInput, { target: { value: 'testuser' } });
    await fireEvent.input(passwordInput, { target: { value: 'password123' } });
    await fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeTruthy();
    });
  });

  it('persists token in localStorage after login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'fake-token-12345', token_type: 'bearer' }),
    });

    render(App);

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await fireEvent.input(usernameInput, { target: { value: 'testuser' } });
    await fireEvent.input(passwordInput, { target: { value: 'password123' } });
    await fireEvent.click(submitButton);

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('fake-token-12345');
    });
  });

  it('restores session from localStorage on mount', async () => {
    localStorage.setItem('access_token', 'existing-token');
    localStorage.setItem('username', 'existinguser');

    // Mock /auth/me endpoint to validate token
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ username: 'existinguser', email: 'user@example.com' }),
    });

    render(App);

    // Should skip login form and show file upload after validation
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /Sign In/i })).toBeFalsy();
      expect(screen.getByText(/Drop your video file here/i)).toBeTruthy();
      expect(screen.getByText('existinguser')).toBeTruthy();
    });
  });

  it('clears token and shows login on logout', async () => {
    localStorage.setItem('access_token', 'existing-token');
    localStorage.setItem('username', 'existinguser');

    // Mock /auth/me endpoint for initial session restore
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ username: 'existinguser', email: 'user@example.com' }),
    });

    render(App);

    // Wait for session to restore
    await waitFor(() => {
      expect(screen.getByText('existinguser')).toBeTruthy();
    });

    // Click user menu to open dropdown
    const userButton = screen.getByLabelText(/User menu/i);
    await fireEvent.click(userButton);

    // Click logout button
    const logoutButton = screen.getByText(/Logout/i);
    await fireEvent.click(logoutButton);

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(screen.getByRole('heading', { name: /Sign In/i })).toBeTruthy();
    });
  });
});
