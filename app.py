# app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import aiofiles
import asyncio
from datetime import datetime, timedelta
import humanize
from typing import Optional, Callable, TypeVar, ParamSpec, Dict
from fastapi.requests import Request
from functools import wraps

# Initialize FastAPI
app = FastAPI()

# Simple in-memory cache
cache: Dict[str, tuple[any, datetime]] = {}

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
            
            # Check cache
            if cache_key in cache:
                cached_value, timestamp = cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=expire_time):
                    return cached_value
                else:
                    del cache[cache_key]
            
            response = await func(*args, **kwargs)
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
        processor = VideoProcessor(video.url)
        if not await processor.is_duration_valid():
            raise HTTPException(status_code=400, detail="Video duration should not exceed 2 minutes")

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
        raise HTTPException(status_code=500, detail=str(e))
