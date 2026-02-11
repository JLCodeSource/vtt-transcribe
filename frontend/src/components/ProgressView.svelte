<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { TranscriptionJob, WebSocketMessage, TranscriptSegment } from '../types';

  interface Props {
    job: TranscriptionJob;
    onprogress: (event: CustomEvent<{ status: string }>) => void;
    oncomplete: (event: CustomEvent<TranscriptSegment[]>) => void;
    onerror: (event: CustomEvent<string>) => void;
  }

  const { job, onprogress, oncomplete, onerror }: Props = $props();

  let ws: WebSocket | null = null;
  let statusMessage = $state('Initializing...');

  onMount(() => {
    connectWebSocket();
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
  });

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${job.job_id}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      statusMessage = 'Connected. Processing...';
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data as string) as WebSocketMessage;

        if (message.status === 'processing') {
          statusMessage = 'Processing transcription...';

          const progressEvent = new CustomEvent<{ status: string }>('progress', {
            detail: { status: message.status },
          });
          onprogress(progressEvent);
        } else if (message.status === 'completed') {
          statusMessage = 'Transcription complete!';
          
          // Parse the result to extract segments
          const result = message.result || '';
          const segments = parseTranscriptResult(result);

          const completeEvent = new CustomEvent<TranscriptSegment[]>('complete', {
            detail: segments,
          });
          oncomplete(completeEvent);

          if (ws) {
            ws.close();
          }
        } else if (message.status === 'failed') {
          const errorMsg = message.error || 'Unknown error';
          statusMessage = `Error: ${errorMsg}`;

          const errorEvent = new CustomEvent<string>('error', {
            detail: errorMsg,
          });
          onerror(errorEvent);

          if (ws) {
            ws.close();
          }
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      statusMessage = 'Connection error';
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
  }

  function parseTranscriptResult(result: string): Array<{ start: number; end: number; text: string; speaker?: string }> {
    // Parse the transcript result format: "[MM:SS - MM:SS] text" or "[Speaker] [MM:SS - MM:SS] text"
    const segments: Array<{ start: number; end: number; text: string; speaker?: string }> = [];
    const lines = result.split('\n').filter(line => line.trim());

    for (const line of lines) {
      // Try to match format with speaker: [Speaker] [MM:SS - MM:SS] text
      const speakerMatch = line.match(/^\[([^\]]+)\]\s*\[(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})\]\s*(.+)$/);
      if (speakerMatch) {
        const [, speaker, startMin, startSec, endMin, endSec, text] = speakerMatch;
        segments.push({
          speaker,
          start: parseInt(startMin) * 60 + parseInt(startSec),
          end: parseInt(endMin) * 60 + parseInt(endSec),
          text: text.trim(),
        });
        continue;
      }

      // Try to match format without speaker: [MM:SS - MM:SS] text
      const noSpeakerMatch = line.match(/^\[(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})\]\s*(.+)$/);
      if (noSpeakerMatch) {
        const [, startMin, startSec, endMin, endSec, text] = noSpeakerMatch;
        segments.push({
          start: parseInt(startMin) * 60 + parseInt(startSec),
          end: parseInt(endMin) * 60 + parseInt(endSec),
          text: text.trim(),
        });
      }
    }

    return segments;
  }
</script>

<div class="progress-container">
  <div class="progress-header">
    <h3>Processing: {job.filename}</h3>
    <span class="status-badge" class:processing={job.status === 'processing'}>
      {job.status}
    </span>
  </div>

  <div class="progress-details">
    <span class="status-text">{statusMessage}</span>
  </div>

  <div class="progress-animation">
    {#if job.status === 'processing'}
      <div class="spinner"></div>
    {/if}
  </div>
</div>

<style>
  .progress-container {
    padding: 2rem;
    background: var(--background);
    border-radius: 12px;
    border: 2px solid var(--border-color);
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .progress-header h3 {
    margin: 0;
    font-size: 1.25rem;
    word-break: break-all;
  }

  .status-badge {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    background: var(--text-light);
    color: white;
    font-size: 0.875rem;
    font-weight: 500;
    text-transform: uppercase;
  }

  .status-badge.processing {
    background: var(--warning-color);
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.7;
    }
  }

  .progress-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .status-text {
    color: var(--text-light);
    font-size: 0.875rem;
  }

  .progress-animation {
    display: flex;
    justify-content: center;
    padding: 1rem 0;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
