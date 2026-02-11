import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import AppMinimal from '../App-minimal.svelte';

describe('App-minimal', () => {
  it('renders the main heading', () => {
    render(AppMinimal);
    expect(screen.getByText(/VTT Transcribe Frontend Working!/i)).toBeTruthy();
  });

  it('shows the tagline', () => {
    render(AppMinimal);
    expect(
      screen.getByText(/AI-Powered Video Transcription with Speaker Diarization/i)
    ).toBeTruthy();
  });

  it('renders with initial counter value of 0', () => {
    render(AppMinimal);
    expect(screen.getByText(/Test Counter: 0/i)).toBeTruthy();
  });

  it('increments counter when button is clicked', async () => {
    render(AppMinimal);
    
    const button = screen.getByRole('button', { name: /Click me!/i });
    await fireEvent.click(button);
    
    expect(screen.getByText(/Test Counter: 1/i)).toBeTruthy();
  });

  it('shows list of working Svelte 5 features', () => {
    render(AppMinimal);
    expect(screen.getByText(/Svelte 5 Features Working/i)).toBeTruthy();
    expect(screen.getByText(/Component mounting/i)).toBeTruthy();
    expect(screen.getByText(/Reactive variables with \$state\(\)/i)).toBeTruthy();
    expect(screen.getByText(/Event handlers/i)).toBeTruthy();
    expect(screen.getByText(/Template interpolation/i)).toBeTruthy();
    expect(screen.getByText(/CSS styling/i)).toBeTruthy();
  });
});
