import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import App from '../App.svelte';

describe('App', () => {
  it('renders the main heading', () => {
    render(App);
    expect(screen.getByText(/VTT Transcribe/i)).toBeTruthy();
  });

  it('renders the file upload component initially', () => {
    render(App);
    expect(screen.getByText(/Drop your video file here/i)).toBeTruthy();
  });

  it('shows the tagline', () => {
    render(App);
    expect(
      screen.getByText(/AI-Powered Video Transcription/i)
    ).toBeTruthy();
  });
});
