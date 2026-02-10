/**
 * Vitest setup file for Svelte 5 + jsdom environment.
 *
 * Ensures tests run in a browser-like (client) environment by asserting that
 * the global `window` object is available before any tests execute.
 */

// Set up jsdom environment globals
import { beforeAll } from 'vitest';

beforeAll(() => {
  // Ensure we're in a browser-like environment
  if (typeof window === 'undefined') {
    throw new Error('Test environment is not browser-like. Check vitest config.');
  }
});
