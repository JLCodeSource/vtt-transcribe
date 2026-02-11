<script>
  // Minimal working app
  let message = "VTT Transcribe Frontend Working! ✅";
  let count = 0;
  
  function increment() {
    count += 1;
  }
</script>

<main style="
  font-family: Arial, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  margin: 0;
  min-height: 100vh;
">
  <h1 style="
    color: white;
    font-size: 2rem;
    margin-bottom: 20px;
  ">{message}</h1>
  
  <p style="font-size: 1.2rem; margin: 15px 0;">
    🎬 AI-Powered Video Transcription with Speaker Diarization
  </p>
  
  <div style="
    background: rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
  ">
    <h2>Test Counter: {count}</h2>
    <button 
      on:click={increment}
      style="
        background: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 1rem;
      "
    >
      Click me! (+1)
    </button>
  </div>
  
  <div style="
    background: rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
  ">
    <h3>✅ Svelte 4 Features Working:</h3>
    <ul>
      <li>✅ Component mounting</li>
      <li>✅ Reactive variables ({count})</li>
      <li>✅ Event handlers (click)</li>
      <li>✅ Template interpolation</li>
      <li>✅ CSS styling</li>
    </ul>
  </div>
</main>