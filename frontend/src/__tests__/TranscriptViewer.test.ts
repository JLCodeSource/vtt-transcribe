import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TranscriptViewer from '../components/TranscriptViewer.svelte';
import type { TranscriptSegment } from '../types';

describe('TranscriptViewer', () => {
  const mockSegments: TranscriptSegment[] = [
    {
      start: 0,
      end: 5.5,
      text: 'Hello, this is a test transcript.',
      speaker: 'SPEAKER_00',
    },
    {
      start: 5.5,
      end: 10.2,
      text: 'This is another segment.',
      speaker: 'SPEAKER_01',
    },
  ];

  it('renders the transcript header', () => {
    render(TranscriptViewer, {
      props: {
        segments: mockSegments,
        jobId: 'test-job-123',
        onreset: () => {},
      },
    });
    expect(screen.getByText(/📄 Transcript/i)).toBeTruthy();
  });

  it('displays all segments', () => {
    render(TranscriptViewer, {
      props: {
        segments: mockSegments,
        jobId: 'test-job-123',
        onreset: () => {},
      },
    });
    expect(screen.getByText(/Hello, this is a test transcript./i)).toBeTruthy();
    expect(screen.getByText(/This is another segment./i)).toBeTruthy();
  });

  it('shows download buttons', () => {
    render(TranscriptViewer, {
      props: {
        segments: mockSegments,
        jobId: 'test-job-123',
        onreset: () => {},
      },
    });
    expect(screen.getByRole('button', { name: /Download TXT/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Download VTT/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Download SRT/i })).toBeTruthy();
  });

  it('shows speaker badges', () => {
    render(TranscriptViewer, {
      props: {
        segments: mockSegments,
        jobId: 'test-job-123',
        onreset: () => {},
      },
    });
    expect(screen.getByText('SPEAKER_00')).toBeTruthy();
    expect(screen.getByText('SPEAKER_01')).toBeTruthy();
  });

  it('displays segment count', () => {
    render(TranscriptViewer, {
      props: {
        segments: mockSegments,
        jobId: 'test-job-123',
        onreset: () => {},
      },
    });
    expect(screen.getByText(/Showing 2 of 2 segments/i)).toBeTruthy();
  });
});
