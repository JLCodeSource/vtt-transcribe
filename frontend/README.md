# Frontend Development

This directory contains the Svelte + Vite + TypeScript frontend for VTT Transcribe.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development

The dev server runs on port 3000 and proxies API requests to the backend:

- `/api/*` → `http://api:8000`
- `/ws/*` → `ws://api:8000` (WebSocket)

## Features

- **File Upload**: Drag-and-drop video/audio files
- **Real-time Progress**: WebSocket connection for live transcription updates
- **Transcript Viewer**: Interactive transcript with speaker labels and timestamps
- **Multi-format Export**: Download transcripts as TXT, VTT, or SRT
- **Search & Filter**: Search transcript text and filter by speaker

## Tech Stack

- **Framework**: Svelte 5 (with runes)
- **Build Tool**: Vite
- **Language**: TypeScript
- **Testing**: Vitest + Testing Library
- **Linting**: ESLint + Prettier

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Svelte components
│   │   ├── FileUpload.svelte
│   │   ├── ProgressView.svelte
│   │   └── TranscriptViewer.svelte
│   ├── App.svelte          # Root component
│   ├── main.ts             # Entry point
│   ├── app.css             # Global styles
│   └── types.ts            # TypeScript types
├── public/                 # Static assets
├── index.html             # HTML template
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript config
└── package.json           # Dependencies
```

## Testing

```bash
# Run tests once
npm test

# Run tests in watch mode
npm run test:watch
```

## Code Quality

```bash
# Type checking
npm run check

# Linting
npm run lint

# Formatting
npm run format
```
