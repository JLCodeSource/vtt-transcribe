import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Login from '../components/Login.svelte';

describe('Login', () => {
  it('renders login form', () => {
    render(Login);
    expect(screen.getByRole('heading', { name: /Sign In/i })).toBeTruthy();
    expect(screen.getByLabelText(/username/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
  });

  it('shows register link', () => {
    render(Login);
    expect(screen.getByText(/Don't have an account/i)).toBeTruthy();
    expect(screen.getByText(/Register/i)).toBeTruthy();
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

  it('calls onregister when register link is clicked', async () => {
    const onregister = vi.fn();
    render(Login, { props: { onregister } });

    const registerLink = screen.getByText(/Register/i);
    await fireEvent.click(registerLink);

    expect(onregister).toHaveBeenCalled();
  });
});
