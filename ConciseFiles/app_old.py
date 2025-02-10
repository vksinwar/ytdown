# app.py
import os
from flask import Flask, render_template, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/error")
def error():
    return render_template("error.html")

def is_video_duration_valid(url, max_duration=120):
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        duration = info_dict.get("duration", 0)
        return duration <= max_duration

def download_video(url):
    progress = {"status": "downloading", "progress": 0}

    def progress_hook(d):
        if d["status"] == "downloading":
            progress["progress"] = d["_percent_str"]
            if d["_percent"] == 100:
                progress["status"] = "completed"
                progress["message"] = "Download completed!"

    ydl_opts = {
        "format": "best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "progress_hooks": [progress_hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if is_video_duration_valid(url):  # Check video duration restriction
            ydl.download([url])
        else:
            progress["status"] = "error"
            progress["message"] = "Error: Video duration should not exceed 2 minutes"

    return progress

@app.route("/download", methods=["POST"])
def download():
    try:
        data = request.get_json()
        url = data["url"]

        progress = download_video(url)

        if progress["status"] == "completed":
            return jsonify(message=progress["message"], title="", duration=""), 200
        elif progress["status"] == "error":
            return jsonify(message=progress["message"], title="", duration=""), 400
        else:
            return jsonify(progress=progress["progress"], title="", duration=""), 200
    except Exception as e:
        print(str(e))
        return jsonify(message="Error: Server encountered an issue", title="", duration=""), 500

if __name__ == "__main__":
    app.run()
