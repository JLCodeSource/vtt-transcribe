<script lang="ts">
  interface Props {
    currentPage?: string;
    onnavigate?: (page: string) => void;
  }

  let { currentPage = 'home', onnavigate }: Props = $props();

  const menuItems = [
    { id: 'home', label: 'Home', icon: '🏠' },
    { id: 'jobs', label: 'Jobs', icon: '📋' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
    { id: 'about', label: 'About', icon: 'ℹ️' }
  ];

  function handleNavigate(page: string) {
    if (onnavigate) {
      onnavigate(page);
    }
  }
</script>

<nav class="navigation">
  <div class="nav-header">
    <h2>🎬 VTT</h2>
  </div>

  <ul class="nav-menu">
    {#each menuItems as item}
      <li>
        <button
          class="nav-item"
          class:active={currentPage === item.id}
          onclick={() => handleNavigate(item.id)}
        >
          <span class="nav-icon">{item.icon}</span>
          <span class="nav-label">{item.label}</span>
        </button>
      </li>
    {/each}
  </ul>
</nav>

<style>
  .navigation {
    width: 250px;
    background: white;
    border-right: 1px solid #e5e7eb;
    height: 100vh;
    position: fixed;
    left: 0;
    top: 0;
    display: flex;
    flex-direction: column;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
    z-index: 100;
  }

  .nav-header {
    padding: 1.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .nav-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #667eea;
    font-weight: 700;
  }

  .nav-menu {
    list-style: none;
    padding: 1rem 0;
    margin: 0;
    flex: 1;
  }

  .nav-menu li {
    margin: 0;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.875rem 1.5rem;
    border: none;
    background: none;
    cursor: pointer;
    color: #4b5563;
    font-size: 1rem;
    transition: all 0.2s ease;
    text-align: left;
  }

  .nav-item:hover {
    background: #f3f4f6;
    color: #667eea;
  }

  .nav-item.active {
    background: #eef2ff;
    color: #667eea;
    font-weight: 600;
    border-right: 3px solid #667eea;
  }

  .nav-icon {
    font-size: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
  }

  .nav-label {
    flex: 1;
  }
</style>
