# Cloudflare Camera Deployment Guide

This guide covers how to deploy your secure, rate-limited camera stream to the public internet using Cloudflare Tunnel.

## Prerequisites
- A Cloudflare account.
- A domain name managed in Cloudflare (e.g., `mydomain.com`).

## 1. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

## 2. Configuration
Create a `.env` file (optional, defaults provided):
```bash
cp .env.example .env
```
Edit `.env` to change your token or camera settings:
```ini
CAMERA_TOKEN=your_secure_token_here
MAX_FPS=15
JPEG_QUALITY=70
```

## 3. Deployment
We have provided an automated script `deploy.sh` that handles the heavy lifting.

1.  Run the script:
    ```bash
    ./deploy.sh
    ```
2.  **Follow the prompts**:
    - It will ask to install `cloudflared` if missing.
    - It will ask you to login to Cloudflare (opens browser).
    - It will ask for your desired hostname (e.g., `cam.yourdomain.com`).
3.  **Authentication**:
    Once running, access your camera at:
    `https://cam.yourdomain.com/video_feed?token=your_secure_token_here`

## Manual Run (Development)
If you only want to run the backend locally:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
Access at: `http://localhost:8000/video_feed?token=my_secret_key`

## Troubleshooting
- **403 Forbidden**: You forgot the `?token=...` parameter or it is incorrect.
- **Latency**: Lower `MAX_FPS` or `JPEG_QUALITY` in `.env`.
- **404 Not Found**: Ensure DNS propagation is complete (can take a minute for new tunnels).
