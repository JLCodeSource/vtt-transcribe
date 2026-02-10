<script lang="ts">
  import type { UploadOptions } from '../types';

  interface Props {
    onuploadstart: (event: CustomEvent) => void;
  }

  let { onuploadstart }: Props = $props();

  let isDragging = $state(false);
  let selectedFile: File | null = $state(null);
  let options: UploadOptions = $state({
    diarization: true,
    language: 'auto',
    model: 'whisper-1',
  });
  let isUploading = $state(false);

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragging = true;
  }

  function handleDragLeave() {
    isDragging = false;
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragging = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      selectedFile = files[0];
    }
  }

  function handleFileSelect(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      selectedFile = target.files[0];
    }
  }

  async function handleUpload() {
    if (!selectedFile) return;

    isUploading = true;

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('diarization', String(options.diarization));
      if (options.language !== 'auto') {
        formData.append('language', options.language);
      }
      formData.append('model', options.model);

      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const job = await response.json();

      // Dispatch custom event with job details
      const event = new CustomEvent('uploadstart', { detail: job });
      onuploadstart(event);
    } catch (error) {
      alert(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      isUploading = false;
    }
  }

  function clearFile() {
    selectedFile = null;
  }
</script>

<div class="upload-container">
  <div
    class="dropzone"
    class:dragging={isDragging}
    class:has-file={selectedFile}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
  >
    {#if !selectedFile}
      <div class="dropzone-content">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <h3>Drop your video file here</h3>
        <p>or</p>
        <label for="file-input" class="file-label">
          <button type="button" class="primary" onclick={() => document.getElementById('file-input')?.click()}>
            Choose File
          </button>
        </label>
        <input
          id="file-input"
          type="file"
          accept="video/*,audio/*"
          onchange={handleFileSelect}
          style="display: none;"
        />
        <p class="hint">Supports MP4, AVI, MOV, MP3, WAV, and more</p>
      </div>
    {:else}
      <div class="file-selected">
        <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <div class="file-info">
          <h4>{selectedFile.name}</h4>
          <p>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
        <button type="button" class="clear-btn" onclick={clearFile} disabled={isUploading}>
          ✕
        </button>
      </div>
    {/if}
  </div>

  {#if selectedFile}
    <div class="options">
      <h3>Transcription Options</h3>

      <label class="checkbox-label">
        <input type="checkbox" bind:checked={options.diarization} disabled={isUploading} />
        <span>Enable Speaker Diarization</span>
        <span class="hint-text">Identify different speakers in the audio</span>
      </label>

      <label class="input-label">
        <span>Language</span>
        <select bind:value={options.language} disabled={isUploading}>
          <option value="auto">Auto-detect</option>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="it">Italian</option>
          <option value="pt">Portuguese</option>
          <option value="nl">Dutch</option>
          <option value="pl">Polish</option>
          <option value="ru">Russian</option>
          <option value="ja">Japanese</option>
          <option value="zh">Chinese</option>
        </select>
      </label>

      <label class="input-label">
        <span>Model</span>
        <select bind:value={options.model} disabled={isUploading}>
          <option value="whisper-1">Whisper-1 (Default)</option>
        </select>
      </label>

      <button type="button" class="primary upload-btn" onclick={handleUpload} disabled={isUploading}>
        {isUploading ? 'Uploading...' : 'Start Transcription'}
      </button>
    </div>
  {/if}
</div>

<style>
  .upload-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .dropzone {
    border: 3px dashed var(--border-color);
    border-radius: 12px;
    padding: 3rem;
    text-align: center;
    transition: all 0.3s;
    background: var(--background);
  }

  .dropzone.dragging {
    border-color: var(--primary-color);
    background: rgba(102, 126, 234, 0.05);
    transform: scale(1.02);
  }

  .dropzone.has-file {
    border-color: var(--success-color);
    background: rgba(16, 185, 129, 0.05);
  }

  .dropzone-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .upload-icon {
    width: 80px;
    height: 80px;
    color: var(--primary-color);
    margin-bottom: 1rem;
  }

  .dropzone-content h3 {
    margin: 0;
    font-size: 1.5rem;
    color: var(--text-color);
  }

  .dropzone-content p {
    margin: 0;
    color: var(--text-light);
  }

  .hint {
    font-size: 0.875rem;
    margin-top: 0.5rem !important;
  }

  .file-selected {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1rem;
  }

  .file-icon {
    width: 60px;
    height: 60px;
    color: var(--success-color);
    flex-shrink: 0;
  }

  .file-info {
    flex: 1;
    text-align: left;
  }

  .file-info h4 {
    margin: 0 0 0.25rem 0;
    font-size: 1.125rem;
    word-break: break-all;
  }

  .file-info p {
    margin: 0;
    color: var(--text-light);
    font-size: 0.875rem;
  }

  .clear-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--error-color);
    color: white;
    font-size: 1.25rem;
    padding: 0;
    flex-shrink: 0;
  }

  .options {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 2rem;
    background: var(--background);
    border-radius: 12px;
  }

  .options h3 {
    margin: 0;
    font-size: 1.25rem;
  }

  .checkbox-label {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    cursor: pointer;
  }

  .checkbox-label input[type='checkbox'] {
    width: 20px;
    height: 20px;
    cursor: pointer;
  }

  .checkbox-label > span:first-of-type {
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .hint-text {
    font-size: 0.875rem;
    color: var(--text-light);
  }

  .input-label {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .input-label > span:first-child {
    font-weight: 500;
  }

  .input-label select {
    width: 100%;
  }

  .upload-btn {
    margin-top: 1rem;
    width: 100%;
    padding: 1rem;
    font-size: 1.125rem;
  }
</style>
