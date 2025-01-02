# app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import yt_dlp
import aiofiles
import asyncio
import io
from datetime import datetime, timedelta
import humanize
from typing import Optional, Callable, TypeVar, ParamSpec, Dict
from fastapi.requests import Request
from functools import wraps
import time

# Initialize FastAPI
app = FastAPI()

# Optimize Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=500)  # Compress responses >= 500 bytes

# Mount static files with caching
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
templates = Jinja2Templates(directory="templates")

# Enable CORS with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://instasave.world", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add caching headers middleware
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    # Add caching for static files
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["Vary"] = "Accept-Encoding"
    
    # Add Server-Timing header
    process_time = time.time() - start_time
    response.headers["Server-Timing"] = f"total;dur={process_time*1000:.2f}"
    
    return response

# Simple in-memory cache with size limit
MAX_CACHE_ITEMS = 100
cache: Dict[str, tuple[any, datetime]] = {}

# Cache cleanup function
async def cleanup_old_cache():
    while True:
        try:
            now = datetime.now()
            expired_keys = [
                k for k, v in cache.items() 
                if now - v[1] > timedelta(minutes=5)
            ]
            for k in expired_keys:
                del cache[k]
            
            # Keep cache size in check
            if len(cache) > MAX_CACHE_ITEMS:
                oldest_keys = sorted(
                    cache.keys(), 
                    key=lambda k: cache[k][1]
                )[:len(cache) - MAX_CACHE_ITEMS]
                for k in oldest_keys:
                    del cache[k]
                    
        except Exception:
            pass
        await asyncio.sleep(300)  # Run every 5 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_cache())

class VideoURL(BaseModel):
    url: str

T = TypeVar('T')
P = ParamSpec('P')

def cache_response(expire_time: int = 300) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            if cache_key in cache:
                cached_value, timestamp = cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=expire_time):
                    return cached_value
                else:
                    del cache[cache_key]
            
            response = await func(*args, **kwargs)
            
            # Only cache if we haven't exceeded the limit
            if len(cache) < MAX_CACHE_ITEMS:
                cache[cache_key] = (response, datetime.now())
            return response
        return wrapper
    return decorator

class VideoProcessor:
    def __init__(self, url: str):
        self.url = url
        self.ydl_opts = {
            'quiet': True,
            'format': 'best',
            'no_warnings': True,
            'socket_timeout': 10,  # Timeout for network operations
        }
    
    async def get_info(self) -> dict:
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return await asyncio.to_thread(ydl.extract_info, self.url, download=False)
    
    async def is_duration_valid(self, max_duration: int = 120) -> bool:
        try:
            info = await self.get_info()
            return info.get("duration", 0) <= max_duration
        except Exception:
            return False

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video-downloader")
async def video_downloader(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/short-downloader")
async def short_downloader(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/reels-downloader")
async def reels_downloader(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/story-downloader")
async def story_downloader(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/highlights-downloader")
async def highlights_downloader(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "section": "contact-section"})

@app.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "section": "privacy-section"})

@app.post("/video-info")
@cache_response(expire_time=300)
async def get_video_info(video: VideoURL):
    try:
        processor = VideoProcessor(video.url)
        info = await processor.get_info()
        
        if not info:
            raise HTTPException(status_code=400, detail="Could not fetch video information")

        return {
            'title': info.get('title', ''),
            'duration': humanize.precisedelta(info.get('duration', 0)),
            'thumbnail': info.get('thumbnail', ''),
            'format': info.get('format', ''),
            'valid': await processor.is_duration_valid()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download")
async def download_video(video: VideoURL):
    try:
        processor = VideoProcessor(video.url)
        if not await processor.is_duration_valid():
            raise HTTPException(status_code=400, detail="Video duration should not exceed 2 minutes")

        # Get video info first
        info = await processor.get_info()
        title = info.get('title', 'video')
        ext = info.get('ext', 'mp4')
        
        def custom_hook(d):
            if d['status'] == 'downloading':
                pass
            elif d['status'] == 'finished':
                pass

        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [custom_hook],
            'socket_timeout': 10,
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=False)
            url = info['url']
            
            # Create response headers for browser download
            headers = {
                'Content-Disposition': f'attachment; filename="{title}.{ext}"',
                'Cache-Control': 'no-cache'
            }
            
            # Return a streaming response that will download directly in the browser
            return StreamingResponse(
                io.BytesIO(await asyncio.to_thread(lambda: requests.get(url, timeout=10).content)),
                media_type='application/octet-stream',
                headers=headers
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
