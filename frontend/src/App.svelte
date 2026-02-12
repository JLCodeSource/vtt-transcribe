<script lang="ts">
  import { onMount } from 'svelte';
  import Navigation from './components/Navigation.svelte';
  import UserMenu from './components/UserMenu.svelte';
  import Settings from './components/Settings.svelte';
  import FileUpload from './components/FileUpload.svelte';
  import TranscriptViewer from './components/TranscriptViewer.svelte';
  import ProgressView from './components/ProgressView.svelte';
  import Login from './components/Login.svelte';
  import type { TranscriptionJob, TranscriptSegment } from './types';

  // Auth state
  let isAuthenticated = $state(false);
  let username = $state('Guest');
  let accessToken = $state<string | null>(null);
  let loginError = $state('');
  let loginLoading = $state(false);

  // Page navigation state
  let currentPage = $state('home');
  let settingsOpen = $state(false);

  // Job state
  let currentJob: TranscriptionJob | null = $state(null);
  let transcript: TranscriptSegment[] = $state([]);

  // Restore session from localStorage on mount
  onMount(() => {
    const storedToken = localStorage.getItem('access_token');
    const storedUsername = localStorage.getItem('username');

    if (storedToken && storedUsername) {
      accessToken = storedToken;
      username = storedUsername;
      isAuthenticated = true;
    }
  });

  async function handleLogin(event: CustomEvent<{ username: string; password: string }>) {
    loginLoading = true;
    loginError = '';

    try {
      const formData = new URLSearchParams();
      formData.append('username', event.detail.username);
      formData.append('password', event.detail.password);

      const response = await fetch('/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        const error = await response.json();
        loginError = error.detail || 'Login failed';
        return;
      }

      const data = await response.json();
      accessToken = data.access_token;
      username = event.detail.username;
      isAuthenticated = true;

      // Persist to localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('username', event.detail.username);
    } catch (error) {
      loginError = 'Network error. Please try again.';
    } finally {
      loginLoading = false;
    }
  }

  function handleLogout() {
    isAuthenticated = false;
    username = 'Guest';
    accessToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    currentJob = null;
    transcript = [];
  }

  function handleNavigate(page: string) {
    if (page === 'settings') {
      settingsOpen = true;
    } else {
      currentPage = page;
    }
  }

  function handleUploadStart(event: CustomEvent<TranscriptionJob>) {
    currentJob = event.detail;
    transcript = [];
  }

  function handleProgress(event: CustomEvent<Partial<TranscriptionJob>>) {
    if (currentJob) {
      currentJob = { ...currentJob, ...event.detail };
    }
  }

  function handleComplete(event: CustomEvent<TranscriptSegment[]>) {
    transcript = event.detail;
    if (currentJob) {
      currentJob = { ...currentJob, status: 'completed' };
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

  function openSettings() {
    settingsOpen = true;
  }

  function closeSettings() {
    settingsOpen = false;
  }
</script>

{#if !isAuthenticated}
  <div class="auth-wrapper">
    <div class="auth-header">
      <h1>🎬 VTT Transcribe</h1>
      <p class="auth-subtitle">AI-Powered Video Transcription</p>
    </div>
    <Login 
      onlogin={handleLogin} 
      loading={loginLoading}
      error={loginError}
    />
  </div>
{:else}
  <Navigation {currentPage} onnavigate={handleNavigate} />

  <div class="app-wrapper">
    <header class="app-header">
      <h1>🎬 VTT Transcribe</h1>
      <UserMenu username={username} isLoggedIn={true} onlogout={handleLogout} onsettings={openSettings} />
  </header>

  <main class="main-content">
    {#if currentPage === 'home'}
      <div class="page-header">
        <h2>AI-Powered Video Transcription</h2>
        <p>Upload your video files for automatic transcription with speaker diarization</p>
      </div>

      <div class="content-card">
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
              <TranscriptViewer
                segments={transcript}
                jobId={currentJob.job_id}
                onreset={handleReset}
              />
            {/if}
          </div>
        {/if}
      </div>
    {:else if currentPage === 'jobs'}
      <div class="page-header">
        <h2>📋 Transcription Jobs</h2>
        <p>View and manage your transcription history</p>
      </div>
      <div class="content-card">
        <p class="placeholder-text">Job history coming soon...</p>
      </div>
    {:else if currentPage === 'about'}
      <div class="page-header">
        <h2>ℹ️ About VTT Transcribe</h2>
        <p>Learn more about this application</p>
      </div>
      <div class="content-card">
        <p>
          VTT Transcribe is an AI-powered video transcription tool that uses OpenAI's Whisper model
          for accurate speech-to-text conversion and pyannote.audio for speaker diarization.
        </p>
        <h3>Features:</h3>
        <ul>
          <li>High-quality audio transcription</li>
          <li>Speaker diarization</li>
          <li>Multi-language support</li>
          <li>Automatic translation</li>
          <li>VTT subtitle export</li>
        </ul>
      </div>
    {/if}
  </main>

  <footer class="app-footer">
    <p>Powered by OpenAI Whisper & pyannote.audio</p>
  </footer>
</div>

<Settings isOpen={settingsOpen} onclose={closeSettings} />
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
  }

  .app-wrapper {
    margin-left: 250px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .app-header {
    background: white;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    position: sticky;
    top: 0;
    z-index: 90;
  }

  .app-header h1 {
    margin: 0;
    font-size: 1.5rem;
    color: #667eea;
    font-weight: 700;
  }

  .main-content {
    flex: 1;
    padding: 2rem;
  }

  .page-header {
    text-align: center;
    color: white;
    margin-bottom: 2rem;
  }

  .page-header h2 {
    font-size: 2.5rem;
    margin: 0 0 0.5rem 0;
    font-weight: 700;
  }

  .page-header p {
    font-size: 1.125rem;
    margin: 0;
    opacity: 0.9;
  }

  .content-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    max-width: 1200px;
    margin: 0 auto;
  }

  .content-card h3 {
    color: #111827;
    margin: 1.5rem 0 1rem 0;
  }

  .content-card ul {
    line-height: 1.8;
    color: #374151;
  }

  .placeholder-text {
    text-align: center;
    color: #9ca3af;
    font-size: 1.125rem;
    padding: 3rem;
  }

  .job-section {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .app-footer {
    text-align: center;
    color: white;
    padding: 2rem;
    opacity: 0.8;
    font-size: 0.9rem;
    margin-top: auto;
  }

  .auth-wrapper {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .auth-header {
    text-align: center;
    color: white;
    margin-bottom: 2rem;
  }

  .auth-header h1 {
    font-size: 2.5rem;
    margin: 0 0 0.5rem 0;
    font-weight: 700;
  }

  .auth-subtitle {
    font-size: 1.125rem;
    margin: 0;
    opacity: 0.9;
  }

  .app-footer p {
    margin: 0;
  }
</style>
