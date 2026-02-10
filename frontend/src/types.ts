export interface TranscriptionJob {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

export interface UploadOptions {
  diarization: boolean;
  language?: string;
  model?: string;
}

export interface WebSocketMessage {
  type: 'progress' | 'complete' | 'error';
  job_id: string;
  data: {
    progress?: number;
    status?: string;
    segments?: TranscriptSegment[];
    error?: string;
  };
}
