<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { TranscriptionJob, WebSocketMessage } from '../types';

  interface Props {
    job: TranscriptionJob;
    onprogress: (event: CustomEvent) => void;
    oncomplete: (event: CustomEvent) => void;
    onerror: (event: CustomEvent) => void;
  }

  let { job, onprogress, oncomplete, onerror }: Props = $props();

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
    const wsUrl = `${protocol}//${window.location.host}/ws/${job.id}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      statusMessage = 'Connected. Processing...';
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        if (message.type === 'progress') {
          const progress = message.data.progress || 0;
          const status = message.data.status || 'Processing';
          statusMessage = status;

          const progressEvent = new CustomEvent('progress', {
            detail: { progress, status },
          });
          onprogress(progressEvent);
        } else if (message.type === 'complete') {
          statusMessage = 'Transcription complete!';
          const segments = message.data.segments || [];

          const completeEvent = new CustomEvent('complete', {
            detail: segments,
          });
          oncomplete(completeEvent);

          if (ws) {
            ws.close();
          }
        } else if (message.type === 'error') {
          const errorMsg = message.data.error || 'Unknown error';
          statusMessage = `Error: ${errorMsg}`;

          const errorEvent = new CustomEvent('error', {
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
</script>

<div class="progress-container">
  <div class="progress-header">
    <h3>Processing: {job.filename}</h3>
    <span class="status-badge" class:processing={job.status === 'processing'}>
      {job.status}
    </span>
  </div>

  <div class="progress-bar-container">
    <div class="progress-bar" style="width: {job.progress}%"></div>
  </div>

  <div class="progress-details">
    <span class="progress-text">{job.progress}% complete</span>
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

  .progress-bar-container {
    width: 100%;
    height: 24px;
    background: #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
    border-radius: 12px;
    transition: width 0.3s ease;
    position: relative;
  }

  .progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    animation: shimmer 2s infinite;
  }

  @keyframes shimmer {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }

  .progress-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .progress-text {
    font-weight: 600;
    color: var(--primary-color);
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
