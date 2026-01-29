#!/bin/bash

# Configuration
TUNNEL_NAME="camera-stream"

echo "=== Cloudflare Tunnel Deployment ==="

# 1. Check for cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "[!] cloudflared is not installed."
    echo "    Installing via Homebrew..."
    brew install cloudflared
fi

# 2. Login if needed
if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "[!] No certificate found. Please login to Cloudflare."
    cloudflared tunnel login
fi

# 3. Create Tunnel (if it doesn't exist)
# We capture the output to see if it failed because it exists
cloudflared tunnel create $TUNNEL_NAME || echo "[*] Tunnel might already exist, continuing..."

# 4. Configure Domain
echo ""
read -p "Enter the hostname you want to use (e.g., camera.mydomain.com): " HOSTNAME
echo "[*] Routing DNS for $HOSTNAME to tunnel $TUNNEL_NAME..."
cloudflared tunnel route dns $TUNNEL_NAME $HOSTNAME

# 5. Generate Config
echo "[*] Generating config..."
USER_HOME=$HOME
# Note: This is an approximation. In a real script we'd parse the JSON file to get the UUID.
# For simplicity, we assume the user might need to check the UUID manually or we parse:
TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')
echo "    Tunnel ID: $TUNNEL_ID"

cat > cloudflared/config.yml <<EOL
tunnel: $TUNNEL_ID
credentials-file: $USER_HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:8000
  - service: http_status:404
EOL

echo "[*] Config generated at cloudflared/config.yml"

# 6. Run
echo "[*] Starting FastAPI Server and Cloudflare Tunnel..."
echo "    Access your camera at: https://$HOSTNAME?token=my_secret_key"

# Using a trap to kill both processes on Ctrl+C
trap 'kill %1; kill %2' SIGINT

# Start FastAPI in background
uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers &

# Start Tunnel in background
cloudflared tunnel run --config cloudflared/config.yml $TUNNEL_NAME &

# Wait for background processes
wait
