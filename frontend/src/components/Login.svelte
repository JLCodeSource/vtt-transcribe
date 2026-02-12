<script lang="ts">
  interface Props {
    loading?: boolean;
    error?: string;
    onlogin?: (event: CustomEvent<{ username: string; password: string }>) => void;
    onregister?: () => void;
  }

  let { loading = false, error = '', onlogin, onregister }: Props = $props();

  let username = $state('');
  let password = $state('');

  function handleSubmit(event: Event) {
    event.preventDefault();
    if (onlogin) {
      const customEvent = new CustomEvent('login', {
        detail: { username, password },
      });
      onlogin(customEvent);
    }
  }

  function handleRegisterClick() {
    if (onregister) {
      onregister();
    }
  }
</script>

<div class="login-container">
  <div class="login-card">
    <h2>Sign In</h2>
    <p class="subtitle">Access your transcription workspace</p>

    {#if error}
      <div class="error-message" role="alert">
        {error}
      </div>
    {/if}

    <form onsubmit={handleSubmit}>
      <div class="form-group">
        <label for="username">Username</label>
        <input id="username" type="text" bind:value={username} disabled={loading} required />
      </div>

      <div class="form-group">
        <label for="password">Password</label>
        <input id="password" type="password" bind:value={password} disabled={loading} required />
      </div>

      <button type="submit" disabled={loading} class="submit-button">
        {loading ? 'Signing In...' : 'Sign In'}
      </button>
    </form>

    {#if onregister}
    <div class="register-link">
      <span>Don't have an account?</span>
      <button type="button" onclick={handleRegisterClick} class="link-button"> Register </button>
    </div>
  {/if}
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
    padding: 2rem;
  }

  .login-card {
    background: white;
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    max-width: 400px;
    width: 100%;
  }

  h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.75rem;
    color: #111827;
    text-align: center;
  }

  .subtitle {
    margin: 0 0 2rem 0;
    color: #6b7280;
    text-align: center;
    font-size: 0.875rem;
  }

  .error-message {
    background: #fee2e2;
    color: #991b1b;
    padding: 0.75rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    font-size: 0.875rem;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: #374151;
    font-weight: 500;
    font-size: 0.875rem;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 1rem;
    transition: all 0.2s ease;
    box-sizing: border-box;
  }

  input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  input:disabled {
    background: #f3f4f6;
    cursor: not-allowed;
  }

  .submit-button {
    width: 100%;
    padding: 0.875rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-top: 0.5rem;
  }

  .submit-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .submit-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .register-link {
    margin-top: 1.5rem;
    text-align: center;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .register-link span {
    margin-right: 0.25rem;
  }

  .link-button {
    background: none;
    border: none;
    color: #667eea;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    font-size: 0.875rem;
    text-decoration: underline;
  }

  .link-button:hover {
    color: #764ba2;
  }
</style>
