<script lang="ts">
  // Minimal working Svelte 5 app with proper TypeScript and styling
  const message = $state("VTT Transcribe Frontend Working! ✅");
  let count = $state(0);
  
  function increment() {
    count += 1;
  }
</script>

<main>
  <h1>{message}</h1>
  
  <p class="tagline">
    🎬 AI-Powered Video Transcription with Speaker Diarization
  </p>
  
  <div class="test-section">
    <h2>Test Counter: {count}</h2>
    <button onclick={increment}>
      Click me! (+1)
    </button>
  </div>
  
  <div class="features-section">
    <h3>✅ Svelte 5 Features Working:</h3>
    <ul>
      <li>✅ Component mounting</li>
      <li>✅ Reactive variables with $state() ({count})</li>
      <li>✅ Event handlers (onclick)</li>
      <li>✅ Template interpolation</li>
      <li>✅ CSS styling</li>
    </ul>
  </div>
</main>

<style>
  main {
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    margin: 0;
    min-height: 100vh;
  }

  h1 {
    color: white;
    font-size: 2rem;
    margin-bottom: 20px;
  }

  .tagline {
    font-size: 1.2rem;
    margin: 15px 0;
  }

  .test-section,
  .features-section {
    background: rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
  }

  button {
    background: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1rem;
  }

  button:hover {
    background: #45a049;
  }

  ul {
    list-style-type: none;
    padding-left: 0;
  }

  li {
    margin: 8px 0;
  }
</style>