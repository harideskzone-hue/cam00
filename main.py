
import cv2
import threading
import time
import os
import logging
import secrets
from typing import Union
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyQuery
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load params from .env file
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
FRAME_RATE_CAP = int(os.getenv("MAX_FPS", "15"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "70"))
CAMERA_TOKEN = os.getenv("CAMERA_TOKEN", "my_secret_key")

# Security Dependency
api_key_query = APIKeyQuery(name="token", auto_error=False)

async def check_token(token: str = Depends(api_key_query)):
    if not token or not secrets.compare_digest(token, CAMERA_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing access token"
        )
    return token

class VideoCamera:
    def __init__(self, source: Union[int, str] = 0):
        self.source = source
        self.video = cv2.VideoCapture(self.source)
        self.lock = threading.Lock()
        self.frame = None
        self.running = True
        
        # Calculate target frame interval
        self.target_interval = 1.0 / FRAME_RATE_CAP
        
        if not self.video.isOpened():
             logger.error(f"Could not open video source: {self.source}")
        else:
             logger.info(f"Video source {self.source} opened successfully. Cap: {FRAME_RATE_CAP} FPS, Quality: {JPEG_QUALITY}%")

        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def __del__(self):
        self.release()

    def release(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        if self.video.isOpened():
            self.video.release()
            logger.info("Camera released.")

    def update(self):
        """Thread worker to continuously capture frames."""
        while self.running:
            start_time = time.time()
            
            if self.video.isOpened():
                success, frame = self.video.read()
                if success:
                    with self.lock:
                        # Resize if needed (optional optimization)
                        # frame = cv2.resize(frame, (640, 480))
                        
                        # Encode frame to JPEG with reduced quality
                        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                        if ret:
                            self.frame = buffer.tobytes()
                else:
                    logger.warning("Failed to read frame. Attempting reconnection...")
                    self.video.release()
                    time.sleep(2)
                    try:
                        # Re-parse source if it was an int
                        src = int(self.source) if str(self.source).isdigit() else self.source
                        self.video = cv2.VideoCapture(src)
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
            else:
                 logger.warning("Camera not open. Retrying...")
                 time.sleep(2)
                 try:
                    src = int(self.source) if str(self.source).isdigit() else self.source
                    self.video = cv2.VideoCapture(src)
                 except Exception:
                     pass
            
            # Smart sleep to maintain FPS cap
            elapsed = time.time() - start_time
            sleep_time = max(0, self.target_interval - elapsed)
            time.sleep(sleep_time)

    def get_frame(self):
        with self.lock:
            return self.frame

# Global Camera Instance
camera_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global camera_instance
    
    # Parse source again for init
    source_env = CAMERA_SOURCE
    try:
        source = int(source_env)
    except ValueError:
        source = source_env
        
    camera_instance = VideoCamera(source)
    
    yield
    
    # Shutdown
    if camera_instance:
        camera_instance.release()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

def generate_frames():
    global camera_instance
    while True:
        if camera_instance:
            frame = camera_instance.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
        else:
            break
        # Generator polling rate (can be faster than camera FPS, but no need to be too fast)
        time.sleep(0.02)

@app.get("/video_feed", dependencies=[Depends(check_token)])
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/")
async def index(request: Request):
    # Pass the token/env info if needed, or just let the user append it manually
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    global camera_instance
    status = {
        "status": "unknown",
        "camera_connected": False,
        "fps_cap": FRAME_RATE_CAP
    }
    if camera_instance and camera_instance.video.isOpened():
        status["status"] = "healthy"
        status["camera_connected"] = True
    else:
        status["status"] = "unhealthy"
    return JSONResponse(status)

if __name__ == "__main__":
    import uvicorn
    # proxy_headers=True is important for Cloudflare
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True)
