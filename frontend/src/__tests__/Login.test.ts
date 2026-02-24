import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Login from '../components/Login.svelte';

// Mock fetch globally
global.fetch = vi.fn();

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock OAuth providers fetch that happens on mount
    (global.fetch as any).mockResolvedValue({
      ok: false,
      json: async () => ({ providers: [] }),
    });
  });

  it('renders login form', () => {
    render(Login);
    expect(screen.getByRole('heading', { name: /Sign In/i })).toBeTruthy();
    expect(screen.getByLabelText(/username/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
  });

  it('shows register link when onregister is provided', () => {
    const onregister = vi.fn();
    render(Login, { props: { onregister } });
    expect(screen.getByText(/Don't have an account/i)).toBeTruthy();
    expect(screen.getByText(/Register/i)).toBeTruthy();
  });

  it('hides register link when onregister is not provided', () => {
    render(Login);
    expect(screen.queryByText(/Don't have an account/i)).toBeFalsy();
    expect(screen.queryByText(/Register/i)).toBeFalsy();
  });

  it('calls onlogin callback when form is submitted', async () => {
    const onlogin = vi.fn();
    render(Login, { props: { onlogin } });

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await fireEvent.input(usernameInput, { target: { value: 'testuser' } });
    await fireEvent.input(passwordInput, { target: { value: 'password123' } });
    await fireEvent.click(submitButton);

    expect(onlogin).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: {
          username: 'testuser',
          password: 'password123',
        },
      })
    );
  });

  it('shows error message when provided', () => {
    render(Login, { props: { error: 'Invalid credentials' } });
    expect(screen.getByText(/Invalid credentials/i)).toBeTruthy();
  });

  it('disables submit button when loading', () => {
    render(Login, { props: { loading: true } });
    const submitButton = screen.getByRole('button', { name: /signing in/i });
    expect(submitButton).toHaveProperty('disabled', true);
  });

  it('switches to register mode when register link is clicked', async () => {
    const onregister = vi.fn();
    render(Login, { props: { onregister } });

    const registerLink = screen.getByText(/Register/i);
    await fireEvent.click(registerLink);

    expect(screen.getByRole('heading', { name: /Create Account/i })).toBeTruthy();
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
  });

  it('calls onregister callback when register form is submitted', async () => {
    const onregister = vi.fn();
    render(Login, { props: { onregister } });

    await fireEvent.click(screen.getByText(/Register/i));

    const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;
    const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /create account/i });

    await fireEvent.input(usernameInput, { target: { value: 'newuser' } });
    await fireEvent.input(emailInput, { target: { value: 'newuser@example.com' } });
    await fireEvent.input(passwordInput, { target: { value: 'password123' } });
    await fireEvent.click(submitButton);

    expect(onregister).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: {
          username: 'newuser',
          email: 'newuser@example.com',
          password: 'password123',
        },
      })
    );
  });
});
