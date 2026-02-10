import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import FileUpload from '../components/FileUpload.svelte';

describe('FileUpload', () => {
  it('renders the dropzone', () => {
    render(FileUpload, { props: { onuploadstart: () => {} } });
    expect(screen.getByText(/Drop your video file here/i)).toBeTruthy();
  });

  it('shows the choose file button', () => {
    render(FileUpload, { props: { onuploadstart: () => {} } });
    expect(screen.getByRole('button', { name: /Choose File/i })).toBeTruthy();
  });

  it('displays supported file formats hint', () => {
    render(FileUpload, { props: { onuploadstart: () => {} } });
    expect(screen.getByText(/Supports MP4, AVI, MOV, MP3, WAV, and more/i)).toBeTruthy();
  });
});
