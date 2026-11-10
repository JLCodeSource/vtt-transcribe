# Devcontainer Configuration

This devcontainer provides a development environment for the transcription package and CLI.

## GPU Support (Optional)

The devcontainer is configured with **optional GPU support**:
- On GPU hosts with nvidia-docker: GPU acceleration is automatically available
- On non-GPU hosts: Container runs normally without GPU (no errors)
- Controlled by `hostRequirements.gpu: "optional"` in devcontainer.json

VS Code's devcontainer extension handles GPU detection and gracefully falls back when GPUs are unavailable. No configuration changes needed - it just works on both GPU and non-GPU hosts!

