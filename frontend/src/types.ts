export interface TranscriptionJob {
  job_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
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
  apiKey?: string;
  hfToken?: string;
}

export interface WebSocketMessage {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  filename: string;
  result?: string;
  error?: string;
}
