# Implementation Plan - Cloudflare Tunnel Deployment

Goal: Deploy the FastAPI application to the public internet using Cloudflare Tunnel, with security and optimization enhancements.

## User Review Required
> [!IMPORTANT]
> **Cloudflare Account & Domain**: You must have an active Cloudflare account and a domain managed by Cloudflare to use the DNS routing features in the automated script.

> [!WARNING]
> **Security**: The stream will be accessible via a public URL. We will implement token-based authentication (`?token=your_secret`), but please ensure you choose a strong secret.

## Proposed Changes

### Backend (`main.py`)
- **Security**: Add a dependency to the `/video_feed` endpoint to require a `token` query parameter. Use `secrets.compare_digest` to prevent timing attacks.
- **Proxy Support**: Add `trusted_hosts=["*"]` to `CORSMiddleware` (if needed) and ensure `uvicorn` runs with `proxy_headers=True`.
- **Optimization**: Implement a `MAX_FPS` configuration (default: 15) to cap the frame rate for bandwidth conservation.
- **Dependencies**: Add `python-dotenv` to manage secrets and config.

### Infrastructure (`cloudflared/`)
- Create directory `cloudflared/`.
- Create `cloudflared/config.yml.template`:
    - Maps hostname to `http://localhost:8000`.
    - Includes `no-tls-verify` (not strictly needed for http localhost but good practice to know).
    - Default ingress rules.

### Automation (`deploy.sh`)
- Check for `cloudflared` installation (install via `brew` on Mac if missing).
- Run `cloudflared tunnel login` (if cert missing).
- Create a tunnel named `camera-stream` (if missing).
- Ask user for `HOSTNAME` (e.g., `camera.mydomain.com`).
- Route DNS for the hostname.
- Generate actual `config.yml` from template.
- Start FastAPI app and Cloudflare Tunnel concurrently.

## Verification Plan

### Automated Tests
- None.

### Manual Verification
1.  **Local Token Test**: Verify `http://localhost:8000/video_feed` returns 403/401 without token, and 200 with correct token.
2.  **FPS Limit Test**: Visually verify video smoothness matches expected FPS.
3.  **Deployment**: Run `./deploy.sh` and follow prompts.
4.  **Public Access**: Access `https://<your-hostname>?token=<your-token>` from a mobile device on 4G/5G.
