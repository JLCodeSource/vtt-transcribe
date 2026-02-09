"""Development server entry point for FastAPI application."""

import uvicorn


def main() -> None:
    """Run the FastAPI application with uvicorn."""
    uvicorn.run(
        "vtt_transcribe.api.app:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
