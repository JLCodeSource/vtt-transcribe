import { describe, it, expect } from 'vitest';

describe('Types', () => {
  it('should export TranscriptionJob type', () => {
    type TranscriptionJob = import('../types').TranscriptionJob;
    const job: TranscriptionJob = {
      job_id: 'test-123',
      filename: 'test.mp4',
      status: 'pending',
      progress: 0,
    };
    expect(job.job_id).toBe('test-123');
  });

  it('should export TranscriptSegment type', () => {
    type TranscriptSegment = import('../types').TranscriptSegment;
    const segment: TranscriptSegment = {
      start: 0,
      end: 5,
      text: 'Test text',
      speaker: 'SPEAKER_00',
    };
    expect(segment.text).toBe('Test text');
  });

  it('should export UploadOptions type', () => {
    type UploadOptions = import('../types').UploadOptions;
    const options: UploadOptions = {
      diarization: true,
      language: 'en',
      model: 'whisper-1',
    };
    expect(options.diarization).toBe(true);
  });
});
