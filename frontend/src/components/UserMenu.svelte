<script lang="ts">
  interface Props {
    isLoggedIn?: boolean;
    username?: string;
    onlogout?: () => void;
    onsettings?: () => void;
  }

  let { 
    isLoggedIn = false, 
    username = 'Guest',
    onlogout,
    onsettings
  }: Props = $props();

  let menuOpen = $state(false);

  function toggleMenu() {
    menuOpen = !menuOpen;
  }

  function handleSettings() {
    menuOpen = false;
    if (onsettings) {
      onsettings();
    }
  }

  function handleLogout() {
    menuOpen = false;
    if (onlogout) {
      onlogout();
    }
  }

  // Close menu when clicking outside
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (menuOpen && !target.closest('.user-menu')) {
      menuOpen = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="user-menu">
  <button class="user-button" onclick={toggleMenu} aria-label="User menu">
    <span class="user-avatar">{isLoggedIn ? username[0].toUpperCase() : '👤'}</span>
    <span class="user-name">{username}</span>
    <span class="chevron" class:open={menuOpen}>▼</span>
  </button>

  {#if menuOpen}
    <div class="dropdown-menu">
      {#if !isLoggedIn}
        <div class="menu-item-info">
          <p>Configure your API keys in Settings</p>
        </div>
      {/if}
      
      <button class="menu-item" onclick={handleSettings}>
        <span class="menu-icon">⚙️</span>
        <span>Settings</span>
      </button>

      {#if isLoggedIn}
        <div class="menu-divider"></div>
        <button class="menu-item" onclick={handleLogout}>
          <span class="menu-icon">🚪</span>
          <span>Logout</span>
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .user-menu {
    position: relative;
    display: inline-block;
  }

  .user-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .user-button:hover {
    background: #f9fafb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  }

  .user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .user-name {
    font-weight: 500;
    color: #374151;
  }

  .chevron {
    font-size: 0.625rem;
    color: #9ca3af;
    transition: transform 0.2s ease;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .dropdown-menu {
    position: absolute;
    top: calc(100% + 0.5rem);
    right: 0;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    min-width: 200px;
    z-index: 1000;
    animation: slideDown 0.2s ease;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .menu-item-info {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .menu-item-info p {
    margin: 0;
    font-size: 0.75rem;
    color: #6b7280;
    line-height: 1.4;
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.875rem;
    color: #374151;
    text-align: left;
    transition: background 0.15s ease;
  }

  .menu-item:hover {
    background: #f3f4f6;
  }

  .menu-icon {
    font-size: 1.125rem;
  }

  .menu-divider {
    height: 1px;
    background: #e5e7eb;
    margin: 0.25rem 0;
  }
</style>
