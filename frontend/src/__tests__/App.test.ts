import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import App from '../App.svelte';

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the main heading', () => {
    render(App);
    expect(screen.getByText(/VTT Transcribe/i)).toBeTruthy();
  });

  it('renders login form when not authenticated', () => {
    render(App);
    expect(screen.getByRole('heading', { name: /Sign In/i })).toBeTruthy();
  });

  it('shows the tagline on auth page', () => {
    render(App);
    expect(screen.getByText(/AI-Powered Video Transcription/i)).toBeTruthy();
  });
});
