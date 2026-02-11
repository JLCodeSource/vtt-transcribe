<script lang="ts">
  interface Props {
    isOpen?: boolean;
    onclose?: () => void;
  }

  let { isOpen = false, onclose }: Props = $props();

  // API Key settings
  let openaiKey = $state('');
  let hfToken = $state('');
  let showOpenaiKey = $state(false);
  let showHfToken = $state(false);

  // Translation language setting
  let translationLanguage = $state('none');

  const languages = [
    { value: 'none', label: 'No Translation' },
    { value: 'es', label: 'Spanish (Español)' },
    { value: 'fr', label: 'French (Français)' },
    { value: 'de', label: 'German (Deutsch)' },
    { value: 'it', label: 'Italian (Italiano)' },
    { value: 'pt', label: 'Portuguese (Português)' },
    { value: 'ru', label: 'Russian (Русский)' },
    { value: 'ja', label: 'Japanese (日本語)' },
    { value: 'ko', label: 'Korean (한국어)' },
    { value: 'zh', label: 'Chinese (中文)' }
  ];

  // Load settings from sessionStorage on mount
  $effect(() => {
    if (typeof window !== 'undefined') {
      openaiKey = sessionStorage.getItem('openai_api_key') || '';
      hfToken = sessionStorage.getItem('hf_token') || '';
      translationLanguage = sessionStorage.getItem('translation_language') || 'none';
    }
  });

  // Handle Escape key to close modal
  $effect(() => {
    if (!isOpen || typeof window === 'undefined') return;

    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        handleClose();
      }
    }

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  });

  function handleSave() {
    // Save to sessionStorage (more secure than localStorage for API keys)
    // Keys are kept in memory for the current session only
    if (openaiKey) {
      sessionStorage.setItem('openai_api_key', openaiKey);
    } else {
      sessionStorage.removeItem('openai_api_key');
    }

    if (hfToken) {
      sessionStorage.setItem('hf_token', hfToken);
    } else {
      sessionStorage.removeItem('hf_token');
    }

    sessionStorage.setItem('translation_language', translationLanguage);

    if (onclose) {
      onclose();
    }
  }

  function handleClose() {
    if (onclose) {
      onclose();
    }
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }
</script>

{#if isOpen}
  <div 
    class="modal-backdrop" 
    onclick={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="settings-title"
  >
    <div class="modal">
      <div class="modal-header">
        <h2 id="settings-title">⚙️ Settings</h2>
        <button class="close-button" onclick={handleClose} aria-label="Close">✕</button>
      </div>

      <div class="modal-content">
        <section class="settings-section">
          <h3>API Configuration</h3>
          <p class="section-description">
            Configure your API keys for transcription and diarization features.
          </p>
          <div class="security-notice">
            <span class="notice-icon">🔒</span>
            <p>API keys are stored in your browser session only and are cleared when you close this tab.</p>
          </div>

          <div class="form-group">
            <label for="openai-key">
              OpenAI API Key
              <span class="required">*</span>
            </label>
            <p class="field-help">Required for audio transcription using Whisper</p>
            <div class="input-with-toggle">
              <input
                id="openai-key"
                type={showOpenaiKey ? 'text' : 'password'}
                bind:value={openaiKey}
                placeholder="sk-proj-..."
                class="input-field"
              />
              <button
                class="toggle-button"
                onclick={() => (showOpenaiKey = !showOpenaiKey)}
                aria-label={showOpenaiKey ? 'Hide API key' : 'Show API key'}
              >
                {showOpenaiKey ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="hf-token">
              HuggingFace Token
            </label>
            <p class="field-help">Optional: Required for speaker diarization features</p>
            <div class="input-with-toggle">
              <input
                id="hf-token"
                type={showHfToken ? 'text' : 'password'}
                bind:value={hfToken}
                placeholder="hf_..."
                class="input-field"
              />
              <button
                class="toggle-button"
                onclick={() => (showHfToken = !showHfToken)}
                aria-label={showHfToken ? 'Hide token' : 'Show token'}
              >
                {showHfToken ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
        </section>

        <section class="settings-section">
          <h3>Translation</h3>
          <p class="section-description">
            Select a target language to automatically translate transcripts.
          </p>

          <div class="form-group">
            <label for="translation-lang">
              Target Language
            </label>
            <select
              id="translation-lang"
              bind:value={translationLanguage}
              class="select-field"
            >
              {#each languages as lang}
                <option value={lang.value}>{lang.label}</option>
              {/each}
            </select>
          </div>
        </section>
      </div>

      <div class="modal-footer">
        <button class="button button-secondary" onclick={handleClose}>
          Cancel
        </button>
        <button class="button button-primary" onclick={handleSave}>
          Save Settings
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .modal {
    background: white;
    border-radius: 16px;
    width: 100%;
    max-width: 600px;
    max-height: 90vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    animation: slideUp 0.3s ease;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #111827;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #6b7280;
    cursor: pointer;
    padding: 0.25rem;
    line-height: 1;
    transition: color 0.2s ease;
  }

  .close-button:hover {
    color: #111827;
  }

  .modal-content {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
  }

  .settings-section {
    margin-bottom: 2rem;
  }

  .settings-section:last-child {
    margin-bottom: 0;
  }

  .settings-section h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1.125rem;
    color: #111827;
  }

  .section-description {
    margin: 0 0 1.5rem 0;
    font-size: 0.875rem;
    color: #6b7280;
    line-height: 1.5;
  }

  .security-notice {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.875rem;
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .notice-icon {
    font-size: 1.25rem;
    flex-shrink: 0;
  }

  .security-notice p {
    margin: 0;
    font-size: 0.8125rem;
    color: #166534;
    line-height: 1.5;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
    font-size: 0.875rem;
  }

  .required {
    color: #ef4444;
  }

  .field-help {
    margin: 0 0 0.5rem 0;
    font-size: 0.75rem;
    color: #6b7280;
  }

  .input-with-toggle {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-field {
    flex: 1;
    padding: 0.625rem 3rem 0.625rem 0.875rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 0.875rem;
    font-family: 'Courier New', monospace;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .input-field:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .toggle-button {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.25rem;
    padding: 0.25rem;
    line-height: 1;
    opacity: 0.6;
    transition: opacity 0.2s ease;
  }

  .toggle-button:hover {
    opacity: 1;
  }

  .select-field {
    width: 100%;
    padding: 0.625rem 0.875rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 0.875rem;
    background: white;
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .select-field:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1.5rem;
    border-top: 1px solid #e5e7eb;
  }

  .button {
    padding: 0.625rem 1.25rem;
    border: none;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .button-secondary {
    background: #f3f4f6;
    color: #374151;
  }

  .button-secondary:hover {
    background: #e5e7eb;
  }

  .button-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .button-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
  }
</style>
