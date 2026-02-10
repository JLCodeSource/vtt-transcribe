/**
 * Vitest setup file for Svelte 5 + jsdom environment
 *
 * Ensures that Svelte components are rendered in client mode (not SSR)
 * by setting the appropriate conditions for module resolution.
 */

// Set up jsdom environment globals
import { beforeAll } from 'vitest';

beforeAll(() => {
  // Ensure we're in a browser-like environment
  if (typeof window === 'undefined') {
    throw new Error('Test environment is not browser-like. Check vitest config.');
  }
});
