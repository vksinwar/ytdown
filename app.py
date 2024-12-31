# app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import redis
import aiofiles
import asyncio
from datetime import datetime, timedelta
import humanize
from typing import Optional, Callable, TypeVar, ParamSpec
from fastapi.requests import Request
from functools import wraps

# Initialize FastAPI and Redis
app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoURL(BaseModel):
    url: str

T = TypeVar('T')
P = ParamSpec('P')

def cache_response(expire_time: int = 300) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            if cached_response := redis_client.get(cache_key):
                return eval(cached_response)
            
            response = await func(*args, **kwargs)
            redis_client.setex(cache_key, expire_time, str(response))
            return response
        return wrapper
    return decorator

class VideoProcessor:
    def __init__(self, url: str):
        self.url = url
        self.ydl_opts = {
            'quiet': True,
            'format': 'best',
            'no_warnings': True
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
        # Check cache for recent downloads
        cache_key = f"download:{video.url}"
        if redis_client.get(cache_key):
            return JSONResponse(content={"message": "Video was recently downloaded, please wait before trying again"}, status_code=429)

        if not await is_video_duration_valid(video.url):
            raise HTTPException(status_code=400, detail="Video duration should not exceed 2 minutes")

        # Set download flag in cache
        redis_client.setex(cache_key, 60, "downloading")  # Prevent repeated downloads for 1 minute

        progress = {"status": "downloading", "progress": 0}

        def progress_hook(d):
            if d['status'] == 'downloading':
                progress['progress'] = d.get('_percent_str', '0%')
                progress['speed'] = d.get('_speed_str', '')
                progress['eta'] = d.get('_eta_str', '')
            elif d['status'] == 'finished':
                progress['status'] = 'completed'
                progress['message'] = 'Download completed!'

        ydl_opts = {
            'format': 'best',
            'outtmpl': f'downloads/{datetime.now().strftime("%Y%m%d_%H%M%S")}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
        }

        # Run download in thread pool to not block
        await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(ydl_opts).download([video.url]))
        
        return {"message": "Download successful", "progress": progress}

    except Exception as e:
        # Remove download flag if error occurs
        redis_client.delete(cache_key)
        raise HTTPException(status_code=500, detail=str(e))
