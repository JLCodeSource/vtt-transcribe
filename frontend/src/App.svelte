<script lang="ts">
  import FileUpload from './components/FileUpload.svelte';
  import TranscriptViewer from './components/TranscriptViewer.svelte';
  import ProgressView from './components/ProgressView.svelte';
  import type { TranscriptionJob, TranscriptSegment } from './types';

  let currentJob: TranscriptionJob | null = $state(null);
  let transcript: TranscriptSegment[] = $state([]);

  function handleUploadStart(event: CustomEvent<TranscriptionJob>) {
    currentJob = event.detail;
    transcript = [];
  }

  function handleProgress(event: CustomEvent<{ progress: number; status: string }>) {
    if (currentJob) {
      currentJob = { ...currentJob, ...event.detail };
    }
  }

  function handleComplete(event: CustomEvent<TranscriptSegment[]>) {
    transcript = event.detail;
    if (currentJob) {
      currentJob = { ...currentJob, status: 'completed', progress: 100 };
    }
  }

  function handleError(event: CustomEvent<string>) {
    if (currentJob) {
      currentJob = { ...currentJob, status: 'failed' };
    }
    alert(`Error: ${event.detail}`);
  }

  function handleReset() {
    currentJob = null;
    transcript = [];
  }
</script>

<main class="container">
  <header>
    <h1>🎬 VTT Transcribe</h1>
    <p>AI-Powered Video Transcription with Speaker Diarization</p>
  </header>

  <div class="app-content">
    {#if !currentJob}
      <FileUpload onuploadstart={handleUploadStart} />
    {:else}
      <div class="job-section">
        <ProgressView
          job={currentJob}
          onprogress={handleProgress}
          oncomplete={handleComplete}
          onerror={handleError}
        />

        {#if transcript.length > 0}
          <TranscriptViewer segments={transcript} jobId={currentJob.id} onreset={handleReset} />
        {/if}
      </div>
    {/if}
  </div>

  <footer>
    <p>Powered by OpenAI Whisper & pyannote.audio</p>
  </footer>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  header {
    text-align: center;
    color: white;
    margin-bottom: 3rem;
  }

  header h1 {
    font-size: 3rem;
    margin: 0 0 0.5rem 0;
    font-weight: 700;
  }

  header p {
    font-size: 1.2rem;
    margin: 0;
    opacity: 0.9;
  }

  .app-content {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    min-height: 400px;
  }

  .job-section {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  footer {
    text-align: center;
    color: white;
    margin-top: 2rem;
    opacity: 0.8;
    font-size: 0.9rem;
  }
</style>
